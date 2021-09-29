import logging
import tornado.web
import bleach
from typing import (
    Union,
    List,
    Optional
)

from app.classes.shared.main_controller import Controller

logger = logging.getLogger(__name__)


class BaseHandler(tornado.web.RequestHandler):

    nobleach = {bool, type(None)}
    redactables = ("pass", "api")

    def initialize(self, controller : Controller = None, tasks_manager=None, translator=None):
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

    def autobleach(self, name, text):
        for r in self.redactables:
            if r in name:
                logger.debug("Auto-bleaching {}: {}".format(name, "[**REDACTED**]"))
                break
            else:
                logger.debug("Auto-bleaching {}: {}".format(name, text))
        if type(text) in self.nobleach:
            logger.debug("Auto-bleaching - bypass type")
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
        return self.autobleach(name, arg)

    def get_arguments(self, name: str, strip: bool = True) -> List[str]:
        assert isinstance(strip, bool)
        args = self._get_arguments(name, self.request.arguments, strip)
        args_ret = []
        for arg in args:
            args_ret += self.autobleach(name, arg)
        return args_ret
