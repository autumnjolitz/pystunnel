import asyncio
import logging

from . import StripServer, WrapServer
from . import logger


def create_ssl_strip_server(
        local_port, remote_port, *, loop=None,
        remote_host=None, override_ssl_hostname=None):
    loop = loop or asyncio.get_event_loop()
    server = StripServer(
        local_port, remote_port, loop=loop, destination_host=remote_host,
        override_ssl_hostname=override_ssl_hostname)
    server_future = server.create_server()
    asyncio.async(server_future)
    loop.run_forever()


def create_ssl_wrap_server(
        cert_path, key_path, local_port, remote_port, *,
        loop=None, host=None, remote_host=None):
    loop = loop or asyncio.get_event_loop()
    server = WrapServer(
        local_port, remote_port,
        cert_path, key_path, loop=loop,
        host=host,
        destination_host=remote_host)
    server_future = server.create_server()
    asyncio.async(server_future)
    loop.run_forever()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true', default=False)

    subparsers = parser.add_subparsers()

    tls_strip = subparsers.add_parser(
        'strip', help='Create unecrypted tunnel to encrypted endpoint')
    tls_strip.set_defaults(mode=create_ssl_strip_server)
    tls_wrap = subparsers.add_parser(
        'wrap', help='Create encrypted tunnel to unencrypted endpoint.')
    tls_wrap.set_defaults(mode=create_ssl_wrap_server)

    tls_strip.add_argument(
        '--override-ssl-hostname',
        type=str, default=None,
        help='Override the server_name sent in for TLS validation. '
             'Required for localhost (may be \'\' to accept anything) because most TLS '
             'certs are bonded to the external hostname, whereas localhost '
             'connections want to authorize against the "localhost" host, which there isn\'t '
             'a certificate for.')
    tls_wrap.add_argument('-c', '--cert-path', type=str, help='cert file', required=True)
    tls_wrap.add_argument('-k', '--key-path', type=str, help='key file', required=True)
    tls_wrap.add_argument('host', type=str, help='host/ip to serve from.')
    for _parser in (tls_strip, tls_wrap):
        _parser.add_argument('local_port', type=int)
        _parser.add_argument('remote_port', type=int)
        _parser.add_argument('remote_host', type=str, default='localhost', nargs='?')

    args = parser.parse_args()

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'))
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    if args.debug:
        logger.setLevel(logging.DEBUG)

    if args.remote_host in ('::1', 'localhost', '127.0.0.1') and \
            args.mode is create_ssl_strip_server:
        if args.override_ssl_hostname is None:
            raise SystemExit('--override-ssl-hostname must be specified for localhost remotes.')
        if not args.override_ssl_hostname:
            logger.warning(
                'Override SSL hostname is set to an empty string. '
                'This means ZERO TLS verification will happen. As you\'re on localhost, '
                'it\'s probably not an issue. Still, consider yourself warned.')
    options = dict(args.__dict__)
    del options['debug']
    del options['mode']
    args.mode(**options)
