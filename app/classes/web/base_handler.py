import logging
import tornado.web
import bleach
from typing import (
    Union,
    List,
    Optional
)

logger = logging.getLogger(__name__)


class BaseHandler(tornado.web.RequestHandler):

    nobleach = {bool, type(None)}

    def initialize(self, controller=None, tasks_manager=None, translator=None):
        self.controller = controller
        self.tasks_manager = tasks_manager
        self.translator = translator

    def get_remote_ip(self):
        remote_ip = self.request.headers.get("X-Real-IP") or \
                    self.request.headers.get("X-Forwarded-For") or \
                    self.request.remote_ip
        return remote_ip

    def get_current_user(self):
        return self.get_secure_cookie("user", max_age_days=1)

    def autobleach(self, text):
        if type(text) in self.nobleach:
            return text
        else:
            return bleach.clean(text)

    def get_argument(
            self,
            name: str,
            default: Union[None, str, tornado.web._ArgDefaultMarker] = tornado.web._ARG_DEFAULT,
            strip: bool = True,
            ) -> Optional[str]:
        arg = self._get_argument(name, default, self.request.arguments, strip)
        logger.debug("Bleaching {}: {}".format(name, arg))
        return self.autobleach(arg)

    def get_arguments(self, name: str, strip: bool = True) -> List[str]:
        assert isinstance(strip, bool)
        args = self._get_arguments(name, self.request.arguments, strip)
        args_ret = []
        for arg in args:
            logger.debug("Bleaching {}: {}".format(name, arg))
            args_ret += self.autobleach(arg)
        return args_ret
