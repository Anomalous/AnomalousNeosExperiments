#!/usr/bin/env python3

# Runs a web server which responds to any request with a random image from the current directory.
# This is just a quick example script not a properly fleshed out application.

from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import random

HTTP_PORT = 8080

# known image extensions and their associated content type
IMAGE_TYPES = { '.jpg' : 'image/jpeg', '.jpeg' : 'image/jpeg', '.png' : 'image/png', '.gif' : 'image/gif' }

# store list of all image files at startup so we're not re-scanning all the time
# (though re-scanning might be appropriate for a normal web server)
image_files = []


def main():

    # scan directory for image files
    image_files.extend(find_image_files(os.path.dirname(__file__)))
    if len(image_files) == 0:
        print("No image files found")
        return
    else:
        print("Found {} image files".format(len(image_files)))

    # start HTTP server, use Ctrl-C to terminate
    try:
        http_server = RandomImageHttpServer()
        print("Starting HTTP server...")
        http_server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down HTTP server.")
        http_server.socket.close()


# get list of all image files in the specified directory
def find_image_files(dir_path, recurse=False):
    
    if not os.path.isdir(dir_path):
        return []

    def is_image(file_name):
        ext = os.path.splitext(file_name)[1]
        return os.path.isfile(file_name) and ext.lower() in IMAGE_TYPES.keys()

    image_files = []
    file_paths = [os.path.join(dir_path, fname) for fname in os.listdir(dir_path)]
    for fpath in file_paths:
        if is_image(fpath):
            image_files.append(fpath)
        elif recurse and os.path.isdir(fpath):
            temp = find_image_files(fpath, True)
            image_files.extend(temp)

    return image_files


class RandomImageHttpServer(HTTPServer):

    def __init__(self):
        super(RandomImageHttpServer, self).__init__(('', HTTP_PORT), RandomImageHttpHandler)


class RandomImageHttpHandler(BaseHTTPRequestHandler):

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):

        # Note: normally you would inspect self.path here to serve different content based on the requested path.
        # We're going to ignore that entirely and always send out a randomly chosen image.

        # select random image, determine type from extension, read size and modified date, 
        # if we're processing a GET request read the file data
        img_file = image_files[random.randint(0, len(image_files) - 1)]
        content_type = IMAGE_TYPES[os.path.splitext(img_file)[1].lower()]
        content_size = os.path.getsize(img_file)
        last_modified = os.path.getmtime(img_file)
        if self.command == 'GET':
            with open(img_file, 'rb') as f:
                content = f.read()
        
        # send headers
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', content_size)
        self.send_header('Last-Modified', self.date_time_string(last_modified))
        self.end_headers()

        # send content if this was a 'GET' request (might have been 'HEAD' request instead which sends only headers)
        if self.command == 'GET':
            self.wfile.write(content)


if __name__ == '__main__':
    main()
