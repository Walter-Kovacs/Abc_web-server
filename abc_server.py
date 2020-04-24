import time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

class RH(SimpleHTTPRequestHandler):
    def do_GET(self):
        print("do_GET RH", time.time())
        time.sleep(5)
        SimpleHTTPRequestHandler.do_GET(self)

def run(server_class=ThreadingHTTPServer, handler_class=RH):
    server_address = ('localhost', 80)
    httpd = server_class(server_address, handler_class)
    print("Python system version:", handler_class.sys_version)
    print("Server version:", handler_class.server_version)
    httpd.serve_forever()

if __name__ == "__main__":
    run()
