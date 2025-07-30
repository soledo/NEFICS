#!/usr/bin/env python3

# Standard imports
import os
from typing import Union
from socketserver import ThreadingMixIn
from socket import socket
from http.server import SimpleHTTPRequestHandler, HTTPServer
# NEFICS imports
from nefics.modules.devicebase import DeviceBase, ProtocolListener

class NEFICSHTTPServer(ThreadingMixIn, HTTPServer):

    def __init__(self, *args, server_header : str = 'Python/3.0', static_dir : str = 'html/', **kwargs):
        super().__init__(*args, **kwargs)
        self._server_header : str = server_header
        self._static_dir : str = os.path.abspath(static_dir)
    
    @property
    def server_header(self) -> str:
        return self._server_header
    
    @property
    def static_dir(self) -> str:
        return self._static_dir

class HTTPHandler(SimpleHTTPRequestHandler):

    def __init__(self, request: Union[socket, tuple[bytes,socket]], client_address: Union[tuple[str,int], str] , server: NEFICSHTTPServer, *, directory: Union[str, None] = None):
        super().__init__(request, client_address, server, directory=directory)
        self.server : NEFICSHTTPServer = server

    def translate_path(self, path: str) -> str:
        path = super().translate_path(path)
        return os.path.join(self.server.static_dir, os.path.relpath(path, self.directory))
    
    def replace_content(self, content:bytes) -> bytes:
        #TODO: Update html content
        return content
    
    def version_string(self) -> str:
        return self.server.server_header

    def do_GET(self) -> None:
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            index_path = os.path.join(path, 'index.html')
            if os.path.exists(index_path):
                path = index_path
            else:
                self.send_error(404, "Not found")
                return
        try:
            with open(path, 'rb') as file:
                content = file.read()
                content = self.replace_content(content)
                self.send_response(200)
                self.send_header('Content-Type', self.guess_type(path) if path.lower().split('.')[-1] != 'asp' else 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
        except IOError:
            self.send_error(404, 'Not found')

class HTTPListener(ProtocolListener):

    def __init__(self, *args, server_header : str = 'Python/3.0', static_dir : str = 'html/', port : int = 80, **kwargs):
        super().__init__(*args, device=DeviceBase(guid=0), **kwargs)
        self._httpd : NEFICSHTTPServer = NEFICSHTTPServer(('', port), HTTPHandler, server_header=server_header, static_dir=static_dir)
        self._httpd.timeout = 2.0

    def run(self):
        while not self._terminate:
            self._httpd.handle_request()
        self._httpd.server_close()
