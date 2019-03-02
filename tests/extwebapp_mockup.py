import cgi
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import re
import urllib
from tests.config_extwebapp import ExtWebappConfig

""" test commands
    curl http://localhost:8090/
    curl http://localhost:8090/getunsignedxml
    curl http://localhost:8090/showresult
    curl --data "signedxml=<tests/testdata/xmlsig_response.xml" http://localhost:8090/postsignedxml
"""

def main():
    c = ExtWebappConfig
    print(f"starting {__file__} at {c.host}:{c.port}")
    httpd = HTTPServer((c.host, c.port), RequestHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


class RequestHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.cfg = ExtWebappConfig
        with self.cfg.test_unsignedxml.open('rb') as fd:
            self.test_unsignedxml = fd.read()
        with self.cfg.test_expexted_signedxml.open('rb') as fd:
            self.expected_signedxml = fd.read()
        super().__init__(*args, **kwargs)

    def do_GET(self):
        def redirect_to_sigproxy():
            self.send_response(301)
            redir_to = ExtWebappConfig.load_sigproxy_url(sigtype='samled')
            self.send_header('Location', redir_to)
            self.end_headers()

        def do_unsignedxml_path():
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.test_unsignedxml)

        def do_resultpage():
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'complete.')

        logging.info(f"GET {self.path}")
        if re.match(self.cfg.unsignedxml_path, self.path):
            do_unsignedxml_path()
        elif re.match(self.cfg.returnto_path, self.path):
            do_resultpage()
        else:
            redirect_to_sigproxy()

    def do_POST(self):
        logging.info(f"POST {self.path}")
        if not re.match(self.cfg.returnsignedxml_path, self.path):
            self.send_response(404, 'no POST service at this path')
        post_vars = self._parse_postvars()
        signedxml = post_vars[b'signedxml'][0]
        signedxml_lines = re.split(r'\r\n', signedxml.decode('utf-8').rstrip())
        signedxml_normalized_lineending = '\n'.join(signedxml_lines)
        if self.expected_signedxml != signedxml_normalized_lineending:
            logging.error("Signed XML not matching expected data:\n" + signedxml_normalized_lineending[0:200])

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(self.expected_signedxml)

    def _parse_postvars(self) -> dict:
        ctype, pdict = cgi.parse_header(self.headers['content-type'])
        if ctype == 'multipart/form-data':
            postvars = cgi.parse_multipart(self.rfile, pdict)
        elif ctype == 'application/x-www-form-urlencoded':
            length = int(self.headers['content-length'])
            postvars = cgi.parse_qs(self.rfile.read(length), keep_blank_values=1)
        else:
            postvars = {}
        return postvars


if __name__ == '__main__':
    main()