#!/usr/bin/env python3

# performance monitor reporting machine load statistics over a simple HTTP server
# intended to be used to monitor status of headless servers from within NeosVR world
# format of data is optimized to be read with the simple GET request and LogiX processing supported by Neos

# requires psutil library: https://pypi.org/project/psutil/
# install using 'pip install psutil'
import psutil

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
from time import time

HTTP_PORT = 8082

initial_bytes_sent = 0
initial_bytes_received = 0

previous_bytes_sent = 0
previous_bytes_received = 0
previous_time = 0

class PerfMonHttpHandler(BaseHTTPRequestHandler):
    """HTTP server receives commands and sends sensor data."""

    def do_HEAD(self):
        # do_HEAD() is supposed to send the same headers that it would for an equivalent do_GET() request
        self.do_GET()

    def do_GET(self):
        global previous_bytes_sent, previous_bytes_received, previous_time

        split_path = self.path.rsplit('?')
        path = split_path[0]
        params = parse_qs(split_path[1]) if len(split_path) > 1 else []

        if path == '/':
            self.send_response(301)     # redirect
            self.send_header('Location', '/index.html')
            self.end_headers()
            return

        elif path == '/index.html':
            f = open('index.html', 'r')     # note: would use 'rb' mode for binary files instead of text
            content = f.read()
            f.close()
            content = content.encode('utf-8')
            content_type = 'text/html; charset=utf-8'

        elif path == '/perf-stats':
            # return performance status for computer that perf mon in running on

            # get elapsed time since last time function was run
            time_now = time()
            time_elapsed = time_now - previous_time
            previous_time = time_now

            cpu_percent = psutil.cpu_percent()                      # overall CPU load
            core_percent = max(psutil.cpu_percent(percpu=True))     # highest load on any one CPU core
            mem_total = psutil.virtual_memory().total               # total physical memory, in bytes
            mem_avail = psutil.virtual_memory().available           # available physical memory

            total_bytes_sent = psutil.net_io_counters().bytes_sent - initial_bytes_sent             # bytes sent since program start or last counter reset
            total_bytes_received = psutil.net_io_counters().bytes_recv - initial_bytes_received     # bytes received since program start or last counter reset

            # calculate bandwidth usage
            delta_bytes_sent = total_bytes_sent - previous_bytes_sent
            delta_bytes_received = total_bytes_received - previous_bytes_received
            bps_sent = delta_bytes_sent / time_elapsed                                  # upload bandwidth usage in BYTES per second (not bits)
            bps_received = delta_bytes_received / time_elapsed                          # download bandwidth usage in BYTES per second (not bits)
            previous_bytes_sent = total_bytes_sent
            previous_bytes_received = total_bytes_received
            
            # Note: network traffic has an overhead of somewhere around 15%,
            # so to convert bytes/sec transferred into bits/sec of bandwidth used multiply (bytes/sec * 8 * 1.15)

            # Returned value is simple CSV.
            # We could convert to JSON and parse it in Neos easily enough,
            # but currently JSON parsing in Neos is an inefficient operation.
            # cpu_percent, core_percent, mem_total, mem_avail, total_bytes_sent, total_bytes_received, bytes/sec sent, bytes/sec received
            content = "{}, {}, {}, {}, {}, {}, {}, {}".format(
                cpu_percent, core_percent, mem_total, mem_avail, total_bytes_sent, total_bytes_received, bps_sent, bps_received)

            content = content.encode('utf-8')
            content_type = 'text/plain'

        elif path == '/reset-counters':
            # reset bandwidth counters
            reset_counters()
            content = 'Bandwidth counters reset'
            content = content.encode('utf-8')
            content_type = 'text/plain'

        else:
            self.send_error(404, 'File not found')
            return

        # all normal valid requests end up here
        # always send headers, only send content if command was 'GET' (may have been 'HEAD' instead)
        self.send_headers(content_type, len(content))
        if self.command == 'GET':
            self.wfile.write(content)
            

    def send_headers(self, content_type, content_length):
        # some possible content types: 'application/javascript', 'text/plain', 'text/html; charset=utf-8', 'image/jpeg' 
        self.send_response(200)         # OK
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', content_length)
        self.send_header('Last-Modified', self.date_time_string(time()))
        self.end_headers()


class PerfMonHttpServer(HTTPServer):
    def __init__(self):
        super(PerfMonHttpServer, self).__init__(('', HTTP_PORT), PerfMonHttpHandler)

def reset_counters():
    global initial_bytes_sent, initial_bytes_received, previous_bytes_sent, previous_bytes_received, previous_time
    initial_bytes_sent = psutil.net_io_counters().bytes_sent
    initial_bytes_received = psutil.net_io_counters().bytes_recv
    previous_bytes_sent = initial_bytes_sent
    previous_bytes_received = initial_bytes_received
    previous_time = time()


def main():

    # record initial bytes sent and received so we report only traffic since the program started
    reset_counters()

    """Run HTTP server, function does not return until server is terminated.""" 
    try:
        http_server = PerfMonHttpServer()
        print("Starting HTTP server...")
        http_server.serve_forever()
    except KeyboardInterrupt:
        print("^C received, shutting down HTTP server.")
        http_server.socket.close()



if __name__ == '__main__':
    main()