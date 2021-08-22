from tornado.concurrent import Future
from tornado.escape import utf8
from tornado import gen
from tornado.httpclient import AsyncHTTPClient
from tornado.ioloop import IOLoop
from tornado.options import parse_command_line, define, options
from tornado.web import Application, RequestHandler, stream_request_body

import logging
import toro

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

@stream_request_body
class ProxyHandler(RequestHandler):
    def prepare(self):
        logger.info('ProxyHandler.prepare')
        self.chunks = toro.Queue(1)
        self.fetch_future = AsyncHTTPClient().fetch(
            'http://localhost:%d/upload' % options.port,
            method='PUT',
            body_producer=self.body_producer,
            request_timeout=3600.0)

    @gen.coroutine
    def body_producer(self, write):
        while True:
            chunk = yield self.chunks.get()
            if chunk is None:
                return
            yield write(chunk)

    @gen.coroutine
    def data_received(self, chunk):
        logger.info('ProxyHandler.data_received(%d bytes: %r)',
                     len(chunk), chunk[:9])
        yield self.chunks.put(chunk)

    @gen.coroutine
    def put(self):
        logger.info('ProxyHandler.put')
        # Write None to the chunk queue to signal body_producer to exit,
        # then wait for the request to finish.
        yield self.chunks.put(None)
        response = yield self.fetch_future
        self.set_status(response.code)
        self.write(response.body)

@gen.coroutine
def client():
    @gen.coroutine
    def body_producer(write):
        for i in range(options.num_chunks):
            yield gen.Task(IOLoop.current().call_later, options.client_delay)
            chunk = ('chunk %02d ' % i) * 10000
            logger.info('client writing %d bytes: %r', len(chunk), chunk[:9])
            yield write(utf8(chunk))

    response = yield AsyncHTTPClient().fetch(
        'http://localhost:%d/proxy' % options.port,
        method='PUT',
        body_producer=body_producer,
        request_timeout=3600.0)
    logger.info('client finished with response %d: %r',
                 response.code, response.body)
