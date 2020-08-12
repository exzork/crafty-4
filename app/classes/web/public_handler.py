import sys
import logging
import tornado.web
import tornado.escape

from app.classes.shared.helpers import helper
from app.classes.web.base_handler import BaseHandler
from app.classes.shared.console import console

logger = logging.getLogger(__name__)

try:
    import bleach

except ModuleNotFoundError as e:
    logger.critical("Import Error: Unable to load {} module".format(e, e.name))
    console.critical("Import Error: Unable to load {} module".format(e, e.name))
    sys.exit(1)


class PublicHandler(BaseHandler):

    def set_current_user(self, user):

        expire_days = helper.get_setting("WEB", 'cookie_expire')

        # if helper comes back with false
        if not expire_days:
            expire_days = "5"

        if user:
            self.set_secure_cookie("user", tornado.escape.json_encode(user), expires_days=expire_days)
        else:
            self.clear_cookie("user")

    def get(self, page=None):

        self.clear_cookie("user")
        self.clear_cookie("user_data")

        error = bleach.clean(self.get_argument('error', ""))
        template = "public/404.html"


        if error:
            error_msg = "Invalid Login!"
        else:
            error_msg = ""

        if page == "login":
            template = "public/login.html"
            context = {'error': error_msg}

        # our default 404 template
        else:
            context = {'error': error_msg}

        self.render(template, data=context)

