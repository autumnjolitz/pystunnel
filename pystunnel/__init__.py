import socket
import asyncio
import logging
import weakref
import ssl
import abc
import errno

from .about import __version__
__version__  # Silence unused import warning.

logger = logging.getLogger(__name__)


class Connection(asyncio.Protocol):
    def __init__(self, *, parent_connection=None, loop=None):
        self.origin = 'unallocated-address-{}'.format(id(self))
        self._loop = None
        self.parent = parent_connection
        self.transport = None
        self._closed = False
        self._closing = False
        self._send_queue = []
        self.send_buffer_when_ready = True

        self.logger = logging.getLogger(self.logger_name)

    @property
    def loop(self):
        if self._loop is not None:
            return self._loop()
        return None

    @loop.setter
    def loop(self, val):
        if val is not None:
            assert isinstance(val, asyncio.BaseEventLoop), '{!r} is not a BaseEventLoop'.format(val)
            self._loop = weakref.ref(val)

    @property
    def closed(self):
        return any((self._closing, self._closed))

    @property
    def logger_name(self):
        return '.'.join((__name__, self.__class__.__name__, self.origin))

    def __repr__(self):
        return '{}({}, {})'.format(self.__class__.__name__, self.origin, self.parent)

    def connection_lost(self, exc):
        self.logger.info('has closed {}'.format(
            'due to exception {!r}'.format(exc) if exc else 'normally'))
        if self.parent is not None and not self.parent.closed:
            self.logger.debug('Asking parent {} to close'.format(self.parent))
            loop = self.loop or asyncio.get_event_loop()
            loop.call_later(0.1, self.parent.shutdown)

    def eof_received(self):
        self.logger.debug('{!r} has received an EOF. I will close myself? {}'.format(
            self, 'no' if self.closed else 'yes'))
        return self.closed

    def connection_made(self, transport):
        self.transport = transport
        client, client_port = transport.get_extra_info('peername')
        self.logger.info('Created connection on behalf of {}:{}'.format(client, client_port))
        self.origin = '_of_'.join((client.replace('.', '-'), str(client_port)))
        self.logger.name = self.logger_name

        if self._send_queue and self.send_buffer_when_ready:
            self.write(b'')  # Trigger the send code.

        if self.parent is not None:
            self.parent._on_child_ready(len(self._send_queue))

    def write(self, data):
        if not self.transport:
            self.logger.debug('Queuing data for later')
            self._send_queue.append(data)
            return
        if self._send_queue:
            self.transport.write(b''.join(self._send_queue))
            self._send_queue[:] = []
        self.logger.debug('send {}'.format(data[:128]))

        if data:
            self.transport.write(data)

    def data_received(self, data):
        if self.parent is not None:
            if self.parent.closed:
                self.logger.debug('Lost data {!r}'.format(data[:32]))
                return
            self.parent.write(data)
            return
        self.logger.debug('Data received! {}'.format(data))
        self._handle_data(data)

    @abc.abstractmethod
    def _handle_data(self, data):
        raise NotImplementedError

    def shutdown(self):
        self.logger.debug('Shutdown called')
        self._closing = True

        if self._closed:
            self.logger.debug('Closed already!')
            return

        if not self.transport:
            self.logger.debug('Connection closed before establishing peername')
            return

        if self.transport._closing:
            self.logger.debug('This connection is marked as `closing`')
            return

        if self.transport._buffer:
            loop = self.loop or asyncio.get_event_loop()
            self.logger.debug(
                'This connection is registered as needing to send data. '
                'Waiting for later. Loop provided? {}'.format('yes' if self.loop else 'no'))
            loop.call_later(0.1, self.shutdown)
            return

        if isinstance(self.transport._sock, ssl.SSLSocket):
            try:
                self.transport._sock.shutdown(socket.SHUT_RDWR)
                self.transport._sock.close()
            except socket.error as e:
                if e.errno not in (errno.ECONNABORTED, errno.ENOTCONN):
                    self.logger.exception(
                        'Unexpected issue in shutting down SSL wrapped connection!')
                    raise
        try:
            self.transport.close()
        except IOError as e:
            if e.errno != errno.EBADF:
                self.logger.exception(
                    'Unexpected issue in shutting down transport {!r}'.format(self.transport))
                raise
        else:
            self._closed = True
            self.logger.debug('Close successful.')


class RemoteTLSConnection(Connection):
    def __init__(self, *args, **kwargs):
        self.send_buffer_when_ready = False
        super().__init__(*args, **kwargs)


class ProxiedClientConnection(Connection):

    def __init__(self, server, ssl_hostname=None):
        self.server_ref = weakref.ref(server, lambda ref: self._on_server_lost())
        self.destination_tunnel = RemoteTLSConnection(parent_connection=self, loop=server.loop)
        self._destination_ready = False
        self.ssl_hostname = ssl_hostname
        super().__init__()

    def _on_child_ready(self, send_queue_length=None):
        self._destination_ready = True
        if send_queue_length:
            self.destination_tunnel.write(b'')

    def connection_made(self, transport):
        server = self.server_ref()
        if server is None:
            self.logger.critical('Server inaccessible!')
            raise ValueError

        super().connection_made(transport)
        self.logger.debug('Contacting {}:{} (server_hostname override: {})'.format(
            server.destination_host, server.destination_tunnel, self.ssl_hostname))
        asyncio.async(server.loop.create_connection(
            lambda: self.destination_tunnel,
            server.destination_host, server.destination_port,
            ssl=True, server_hostname=self.ssl_hostname))

    def _handle_data(self, data):
        self.destination_tunnel.write(data)

    def _on_server_lost(self):
        self.logger.debug('Server has been deallocated?')
        self.shutdown()


class Server:
    def __init__(self, port, destination_port, *, loop=None, destination_host='localhost',
                 override_ssl_hostname=None):
        assert isinstance(port, int) and port > 1, \
            '{} is not a valid port to mirror on'.format(port)
        assert isinstance(destination_port, int) and destination_port > 1, \
            '{} is not a valid destination port'.format(destination_port)
        self.override_ssl_hostname = override_ssl_hostname
        self.loop = loop
        self.port = port
        self.destination_port = destination_port
        self.protocol_factory = ProxiedClientConnection

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        self.server_socket.bind(('localhost', port))
        self.destination_host = destination_host
        _, self.port = self.server_socket.getsockname()

    def create_server(self, loop=None):
        if loop is not None:
            self.loop = loop
        self.loop = self.loop or asyncio.get_event_loop()
        server = self.loop.create_server(
            lambda: self.protocol_factory(
                self, self.override_ssl_hostname), sock=self.server_socket)
        return server
