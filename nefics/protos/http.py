#!/usr/bin/env python3

# Standard imports
import os
from threading import Thread
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
# NEFICS imports
from nefics.modules.devicebase import ProtocolListener

class HTTPHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, server_header:str='Python/3', static_dir:str='html/', **kwargs):
        self._server_header = server_header
        self._static_dir = os.path.abspath(static_dir)
        super().__init__(*args, **kwargs)
    
    def end_headers(self) -> None:
        self.send_header('Server', self._server_header)
        return super().end_headers()
    
    def translate_path(self, path: str) -> str:
        path = super().translate_path(path)
        return os.path.join(self._static_dir, os.path.relpath(path, self.directory))
    
    def replace_content(self, content:bytes) -> bytes:
        #TODO: Update html content
        return content
    
    def do_GET(self) -> None:
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            self.send_error(404, "File not found")
            return
        try:
            with open(path, 'rb') as file:
                content = file.read()
                content = self.replace_content(content)
                self.send_response(200)
                self.send_header('Content-Type', self.guess_type(path))
                self.send_header('Content-Length', len(content))
                self.end_headers()
                self.wfile.write(content)
        except IOError:
            self.send_error(404, 'File not found')

class HTTPListener(ProtocolListener):

    def __init__(self, *args, server_header : str = 'Python/3.0', static_dir : str = 'html/', port : int = 80, **kwargs):
        super().__init__(*args, **kwargs)
        self._port : int = port
        self._handler = HTTPHandler(server_header=server_header, static_dir=static_dir)

    def run(self):
        httpd = ThreadingHTTPServer(('', self._port), self._handler)
        while not self._terminate:
            httpd.handle_request()
        httpd.server_close()
