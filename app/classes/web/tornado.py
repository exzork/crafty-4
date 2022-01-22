import os
import sys
import json
import asyncio
import logging
import threading

from app.classes.shared.console import console
from app.classes.shared.helpers import helper

logger = logging.getLogger(__name__)

try:
    import tornado.web
    import tornado.ioloop
    import tornado.log
    import tornado.template
    import tornado.escape
    import tornado.locale
    import tornado.httpserver
    from app.classes.web.public_handler import PublicHandler
    from app.classes.web.panel_handler import PanelHandler
    from app.classes.web.default_handler import DefaultHandler
    from app.classes.web.server_handler import ServerHandler
    from app.classes.web.ajax_handler import AjaxHandler
    from app.classes.web.api_handler import ServersStats, NodeStats
    from app.classes.web.websocket_handler import SocketHandler
    from app.classes.web.static_handler import CustomStaticHandler
    from app.classes.shared.translation import translation
    from app.classes.web.upload_handler import UploadHandler
    from app.classes.web.http_handler import HTTPHandler, HTTPHandlerPage
    from app.classes.web.status_handler import StatusHandler

except ModuleNotFoundError as e:
    logger.critical("Import Error: Unable to load {} module".format(e, e.name))
    console.critical("Import Error: Unable to load {} module".format(e, e.name))
    sys.exit(1)



class Webserver:

    def __init__(self, controller, tasks_manager):
        self.ioloop = None
        self.HTTP_Server = None
        self.HTTPS_Server = None
        self.controller = controller
        self.tasks_manager = tasks_manager
        self._asyncio_patch()


    @staticmethod
    def log_function(handler):

        info = {
            'Status_Code': handler.get_status(),
            'Method': handler.request.method,
            'URL': handler.request.uri,
            'Remote_IP': handler.request.remote_ip,
            'Elapsed_Time': '%.2fms' % (handler.request.request_time() * 1000)
        }

        tornado.log.access_log.info(json.dumps(info, indent=4))

    @staticmethod
    def _asyncio_patch():
        """
        As of Python 3.8 (on Windows), the asyncio default event handler has changed to "proactor",
        where tornado expects the "selector" handler.

        This function checks if the platform is windows and changes the event handler to suit.

        (Taken from https://github.com/mkdocs/mkdocs/commit/cf2b136d4257787c0de51eba2d9e30ded5245b31)
        """
        logger.debug("Checking if asyncio patch is required")
        if sys.platform.startswith("win") and sys.version_info >= (3, 8):
            import asyncio
            try:
                from asyncio import WindowsSelectorEventLoopPolicy
            except ImportError:
                logger.debug("asyncio patch isn't required")
                pass  # Can't assign a policy which doesn't exist.
            else:
                if not isinstance(asyncio.get_event_loop_policy(), WindowsSelectorEventLoopPolicy):
                    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
                    logger.debug("Applied asyncio patch")

    def run_tornado(self):

        # let's verify we have an SSL cert
        helper.create_self_signed_cert()

        http_port = helper.get_setting('http_port')
        https_port = helper.get_setting('https_port')
        
        debug_errors = helper.get_setting('show_errors')
        cookie_secret = helper.get_setting('cookie_secret')

        if cookie_secret is False:
            cookie_secret = helper.random_string_generator(32)

        if not http_port:
            http_port = 8000

        if not https_port:
            https_port = 8443

        cert_objects = {
            'certfile': os.path.join(helper.config_dir, 'web', 'certs', 'commander.cert.pem'),
            'keyfile': os.path.join(helper.config_dir, 'web', 'certs', 'commander.key.pem'),
        }

        logger.info("Starting Web Server on ports http:{} https:{}".format(http_port, https_port))

        asyncio.set_event_loop(asyncio.new_event_loop())

        tornado.template.Loader('.')

        # TODO: Remove because we don't and won't use
        tornado.locale.set_default_locale('en_EN')

        handler_args = {"controller": self.controller, "tasks_manager": self.tasks_manager, "translator": translation}
        handlers = [
            (r'/', DefaultHandler, handler_args),
            (r'/public/(.*)', PublicHandler, handler_args),
            (r'/panel/(.*)', PanelHandler, handler_args),
            (r'/server/(.*)', ServerHandler, handler_args),
            (r'/ajax/(.*)', AjaxHandler, handler_args),
            (r'/api/stats/servers', ServersStats, handler_args),
            (r'/api/stats/node', NodeStats, handler_args),
            (r'/ws', SocketHandler, handler_args),
            (r'/upload', UploadHandler, handler_args),
            (r'/status', StatusHandler, handler_args)
            ]

        app = tornado.web.Application(
            handlers,
            template_path=os.path.join(helper.webroot, 'templates'),
            static_path=os.path.join(helper.webroot, 'static'),
            debug=debug_errors,
            cookie_secret=cookie_secret,
            xsrf_cookies=True,
            autoreload=False,
            log_function=self.log_function,
            login_url="/login",
            default_handler_class=PublicHandler,
            static_handler_class=CustomStaticHandler,
            serve_traceback=debug_errors,
        )
        HTTPhanders = [(r'/', HTTPHandler, handler_args),
            (r'/public/(.*)', HTTPHandlerPage, handler_args),
            (r'/panel/(.*)', HTTPHandlerPage, handler_args),
            (r'/server/(.*)', HTTPHandlerPage, handler_args),
            (r'/ajax/(.*)', HTTPHandlerPage, handler_args),
            (r'/api/stats/servers', HTTPHandlerPage, handler_args),
            (r'/api/stats/node', HTTPHandlerPage, handler_args),
            (r'/ws', HTTPHandlerPage, handler_args),
            (r'/upload', HTTPHandlerPage, handler_args)]
        HTTPapp = tornado.web.Application(
            HTTPhanders,
            template_path=os.path.join(helper.webroot, 'templates'),
            static_path=os.path.join(helper.webroot, 'static'),
            debug=debug_errors,
            cookie_secret=cookie_secret,
            xsrf_cookies=True,
            autoreload=False,
            log_function=self.log_function,
            default_handler_class = HTTPHandler,
            login_url="/login",
            serve_traceback=debug_errors,
        )

        self.HTTP_Server = tornado.httpserver.HTTPServer(HTTPapp)
        self.HTTP_Server.listen(http_port)

        self.HTTPS_Server = tornado.httpserver.HTTPServer(app, ssl_options=cert_objects)
        self.HTTPS_Server.listen(https_port)

        logger.info("https://{}:{} is up and ready for connections.".format(helper.get_local_ip(), https_port))
        console.info("https://{}:{} is up and ready for connections.".format(helper.get_local_ip(), https_port))

        console.info("Server Init Complete: Listening For Connections:")

        self.ioloop = tornado.ioloop.IOLoop.current()
        self.ioloop.start()

    def stop_web_server(self):
        logger.info("Shutting Down Web Server")
        console.info("Shutting Down Web Server")
        self.ioloop.stop()
        self.HTTP_Server.stop()
        self.HTTPS_Server.stop()
        logger.info("Web Server Stopped")
        console.info("Web Server Stopped")
