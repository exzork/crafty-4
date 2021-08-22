from tornado.concurrent import Future
from tornado.escape import utf8
from tornado import gen
from tornado.httpclient import AsyncHTTPClient
from tornado.ioloop import IOLoop
from tornado.options import parse_command_line, define, options
from tornado.web import Application, RequestHandler, stream_request_body

import logging

logger = logging.getLogger(__name__)


define('server_delay', default=2.0)
define('client_delay', default=1.0)
define('num_chunks', default=40)

@stream_request_body
class UploadHandler(RequestHandler):
    def prepare(self):
        print("In PREPARE")
        logger.info('UploadHandler.prepare')

    @gen.coroutine
    def data_received(self, chunk):
        print("In RECIEVED")
        logger.info('UploadHandler.data_received(%d bytes: %r)',
                     len(chunk), chunk[:9])
        yield gen.Task(IOLoop.current().call_later, options.server_delay)

    def put(self):
        print("In PUT")
        logger.info('UploadHandler.put')
        self.write('ok')
