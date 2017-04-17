import asyncio
import logging

from . import Server
from . import logger


def main(local_port, destination_port, *, loop=None,
         destination_host=None, override_ssl_hostname=None):
    loop = loop or asyncio.get_event_loop()
    server = Server(
        local_port, destination_port, loop=loop, destination_host=destination_host,
        override_ssl_hostname=override_ssl_hostname)
    server_future = server.create_server()
    asyncio.async(server_future)
    loop.run_forever()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true', default=False)
    parser.add_argument('--override-ssl-hostname',
                        type=str, default=None,
                        help='Override the server_name sent in for TLS validation. '
                             'Required for localhost.')
    parser.add_argument('local_port', type=int)
    parser.add_argument('remote_port', type=int)
    parser.add_argument('remote_host', type=str, default='localhost', nargs='?')
    args = parser.parse_args()
    if args.remote_host in ('::1', 'localhost', '127.0.0.1') and not args.override_ssl_hostname:
        raise SystemExit('--override-ssl-hostname must be specified for localhost remotes.')
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'))
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    if args.debug:
        logger.setLevel(logging.DEBUG)
    main(args.local_port, args.remote_port, destination_host=args.remote_host,
         override_ssl_hostname=args.override_ssl_hostname)
