#!/usr/bin/env python

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import SocketServer
import os
import requests
import threading
import socket

def handler2(method, path, headers, request_body):
  print 'in handler2'
  return (601, 'Something', {'X-Header': 'Value'}, 'this is the body')

def default_handler(method, path, headers, request_body):
  print 'in default_handler'
  # returns status_code, status_message, headers (list of key/value pairs), response_body (text or stream)
  return (200, 'OK', {}, '')

class DeproxyHTTPServer(SocketServer.ThreadingMixIn, HTTPServer):
  def __init__(self, server_address, RequestHandlerClass, request_handler=default_handler):
    HTTPServer.__init__(self, server_address, RequestHandlerClass)
    self.request_handler = request_handler

class DeproxyRequestHandler(BaseHTTPRequestHandler):
  def handle_one_request(self):
    """Handle a single HTTP request.

    You normally don't need to override this method; see the class
    __doc__ string for information on how to handle specific HTTP
    commands such as GET and POST.

    """
    print 'in handle_one_request()'
    try:
      self.raw_requestline = self.rfile.readline(65537)
      if len(self.raw_requestline) > 65536:
        self.requestline = ''
        self.request_version = ''
        self.command = ''
        self.send_error(414)
        return
      if not self.raw_requestline:
        self.close_connection = 1
        return
      if not self.parse_request():
        # An error code has been sent, just exit
        return
      self.method()
      self.wfile.flush() #actually send the response if not already done.
    except socket.timeout, e:
      #a read or a write timed out.  Discard this connection
      self.log_error("Request timed out: %r", e)
      self.close_connection = 1
      return

  def method(self):
    print 'in method()'
    self.incoming_request = (self.command, self.path, self.headers, self.rfile)
    resp = self.server.request_handler(method=self.command, path=self.path, headers=self.headers, request_body=self.rfile)
    self.outgoing_response = resp
    response_code = resp[0]
    response_message = resp[1]
    response_headers = resp[2]
    response_body = resp[3]
    self.send_response(response_code, response_message)
    for name, value in response_headers.items():
      self.send_header(name, value)
    self.end_headers()
    self.wfile.write(response_body)
    

def run():
  print('http server is starting...')

  server = 'localhost'
  port = 8081
  server_address = (server, port)
  print 'Creating receiver'
  receiver = DeproxyHTTPServer(server_address, DeproxyRequestHandler, request_handler=handler2)
  print 'Creating server thread'
  server_thread = threading.Thread(target=receiver.handle_request)
  server_thread.daemon = True
  server_thread.start()
  print 'Thread started'
  print 'sending request'
  sent_request = requests.request('GET', 'http://%s:%i/abc/123' % (server,port), return_response=False)
  print 'Sent Request:'
  print '  method: %s' % sent_request.method
  print '  url: %s' % sent_request.url
  print '  headers:'
  for name, value in sent_request.headers.items():
    print '    %s: %s' % (name, value)
  print '  data: %s' % sent_request.data
  print ''
  sent_request.send()
  received_response = sent_request.response
  print 'Received Response:'
  print '  url: %s' % received_response.url
  print '  status code: %s' % received_response.status_code
  print '  message: %s' % received_response.raw.reason
  print '  Headers: '
  for name, value in received_response.headers.items():
    print '    %s: %s' % (name, value)
  print '  Body:'
  print received_response.text
  
if __name__ == '__main__':
  run()
