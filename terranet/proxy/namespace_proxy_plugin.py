# -*- coding: utf-8 -*-
"""
    proxy.py
    ~~~~~~~~
    ⚡⚡⚡ Fast, Lightweight, Pluggable, TLS interception capable proxy server focused on
    Network monitoring, controls & Application development, testing, debugging.
    :copyright: (c) 2013-present by Abhinav Singh and contributors.
    :license: BSD, see LICENSE for more details.
"""
import os
import proxy
import netns
from uuid import UUID
from typing import List, Tuple
from urllib import parse as urlparse

from proxy.common.flags import Flags
from proxy.core.connection import TcpClientConnection
from proxy.core.event import EventQueue
from proxy.common.constants import DEFAULT_BUFFER_SIZE
from proxy.common.utils import socket_connection
from proxy.http.parser import HttpParser
from proxy.http.websocket import WebsocketFrame
from proxy.http.server import HttpWebServerBasePlugin, httpProtocolTypes


class NamespaceProxyPlugin(HttpWebServerBasePlugin):
    """Extend in-built Web Server to add Reverse Proxy capabilities.
    This example plugin is equivalent to following Nginx configuration:
        location /get {
            proxy_pass http://httpbin.org/get
        }
    Example:
        $ curl http://localhost:9000/get
        {
          "args": {},
          "headers": {
            "Accept": "*/*",
            "Host": "localhost",
            "User-Agent": "curl/7.64.1"
          },
          "origin": "1.2.3.4, 5.6.7.8",
          "url": "https://localhost/get"
        }
    """

    def __init__(
            self,
            uid: UUID,
            flags: Flags,
            client: TcpClientConnection,
            event_queue: EventQueue):
        super().__init__(uid, flags, client, event_queue)
        self.location = str = r'/*'
        self.upstream: Tuple[str, int] = ('localhost', 80)
        try:
            self.nspid = int(os.environ['NSPID'])
        except KeyError as e:
            raise(EnvironmentError('Environment variable NAMESPACE must be set'
                                   'to run NamespaceProxyPlugin'))

    def routes(self) -> List[Tuple[int, str]]:
        return [
            (httpProtocolTypes.HTTP, self.location),
            (httpProtocolTypes.HTTPS, self.location)
        ]

    def handle_request(self, request: HttpParser) -> None:
        nspid = self.nspid
        with netns.NetNS(nspid=nspid):
            with socket_connection(self.upstream) as conn:
                conn.send(request.build())
                data = conn.recv(DEFAULT_BUFFER_SIZE)
                while(data):
                    self.client.queue(memoryview(data))
                    data = conn.recv(DEFAULT_BUFFER_SIZE)

    def on_websocket_open(self) -> None:
        raise NotImplementedError()

    def on_websocket_message(self, frame: WebsocketFrame) -> None:
        raise NotImplementedError()

    def on_websocket_close(self) -> None:
        raise NotImplementedError()
