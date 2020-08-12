import logging
import tornado.web

logger = logging.getLogger(__name__)


class BaseHandler(tornado.web.RequestHandler):

    def get_remote_ip(self):
        remote_ip = self.request.headers.get("X-Real-IP") or \
                    self.request.headers.get("X-Forwarded-For") or \
                    self.request.remote_ip
        return remote_ip

    def get_current_user(self):
        return self.get_secure_cookie("user", max_age_days=1)
