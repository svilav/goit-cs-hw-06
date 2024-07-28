import http.server
import os
import socket
import socketserver
from datetime import datetime
from multiprocessing import Process
from urllib.parse import parse_qs

from pymongo import MongoClient

HTTP_PORT = 3000
SOCKET_PORT = 5000

client = MongoClient('mongodb://mongo:27017/')
db = client['message_db']
collection = db['messages']


class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'
        elif self.path == '/message':
            self.path = '/message.html'
        else:
            if not os.path.isfile(os.path.join(os.getcwd(), self.path[1:])):
                self.path = '/error.html'

        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path == '/message':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = parse_qs(post_data.decode('utf-8'))
            username = data.get('username', [''])[0]
            message = data.get('message', [''])[0]

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('localhost', SOCKET_PORT))
                s.sendall(f"{username}:{message}".encode('utf-8'))

            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()
        else:
            self.send_error(404)


def run_http_server():
    Handler = MyHttpRequestHandler
    with socketserver.TCPServer(("", HTTP_PORT), Handler) as httpd:
        print(f"Serving HTTP on port {HTTP_PORT}")
        httpd.serve_forever()


def handle_client_connection(client_socket):
    request = client_socket.recv(1024).decode('utf-8')
    username, message = request.split(':')
    document = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        "username": username,
        "message": message
    }
    collection.insert_one(document)
    client_socket.close()


def run_socket_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', SOCKET_PORT))
    server.listen(5)
    print(f'Socket server listening on port {SOCKET_PORT}')
    while True:
        client_sock, address = server.accept()
        handle_client_connection(client_sock)


if __name__ == "__main__":
    http_process = Process(target=run_http_server)
    socket_process = Process(target=run_socket_server)

    http_process.start()
    socket_process.start()

    http_process.join()
    socket_process.join()
