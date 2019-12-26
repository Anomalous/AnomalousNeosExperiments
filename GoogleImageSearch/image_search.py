#!/usr/bin/env python3

# requires Google Images Download library: https://github.com/hardikvasa/google-images-download
# install using 'pip install google_images_download'
from google_images_download import google_images_download

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
from time import time

HTTP_PORT = 8081
SEARCH_COUNT = 50           # number of image URLs to retrieve when a search is run

search_cache = {}

# run an image search using phrase, return count image URLs in a list
def run_image_search(phrase, count):
    response = google_images_download.googleimagesdownload()
    arguments = {"keywords":phrase, "limit":count, "no_download":True}
    result = response.download(arguments)
    return result[0][phrase]

# get a URL for an image from the search results
# uses cached valeu if available, or performs new search if not
def get_image_url(phrase, index):

    print("phrase:", phrase)
    print("index:", index)

    # if search hasn't been run before, run it now
    if phrase not in search_cache:
        search_cache[phrase] = run_image_search(phrase, SEARCH_COUNT)

    # return URL at specified index, if it exists
    urls = search_cache[phrase]
    if len(urls) == 0:
        return ''
    if index < 0:
        return urls[0]
    if index >= len(urls):
        return urls[-1]
    return urls[index]


class ImageSearchHttpHandler(BaseHTTPRequestHandler):
    """HTTP server receives commands and sends sensor data."""

    def do_HEAD(self):
        # do_HEAD() is supposed to send the same headers that it would for an equivalent do_GET() request
        self.do_GET()

    def do_GET(self):

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

        elif path == '/image-search':
            # search for images based on phrase, return single URL based on index
            # results are cached so subsequent calls with a different index don't run another Google search
            # note: cache never clears, so this little script is not good to use for a continually running server

            # parse index, if no index supplied use index of 0
            index = 0
            if 'index' in params:
                try:
                    index = int(params['index'][0])
                except ValueError:
                    pass

            if not 'phrase' in params:
                content = 'please specify a search phrase'
            else:
                content = get_image_url(params['phrase'][0], index)

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


class ImageSearchHttpServer(HTTPServer):
    def __init__(self):
        super(ImageSearchHttpServer, self).__init__(('', HTTP_PORT), ImageSearchHttpHandler)


def main():

    """Run HTTP server, function does not return until server is terminated.""" 
    try:
        http_server = ImageSearchHttpServer()
        print("Starting HTTP server...")
        http_server.serve_forever()
    except KeyboardInterrupt:
        print("^C received, shutting down HTTP server.")
        http_server.socket.close()



if __name__ == '__main__':
    main()