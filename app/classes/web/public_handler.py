import sys
import json
import logging
import tornado.web
import tornado.escape

from app.classes.shared.helpers import helper
from app.classes.web.base_handler import BaseHandler
from app.classes.shared.console import console
from app.classes.shared.models import Users, fn

logger = logging.getLogger(__name__)

try:
    import bleach

except ModuleNotFoundError as e:
    logger.critical("Import Error: Unable to load {} module".format(e, e.name))
    console.critical("Import Error: Unable to load {} module".format(e, e.name))
    sys.exit(1)


class PublicHandler(BaseHandler):

    def set_current_user(self, user):

        expire_days = helper.get_setting('cookie_expire')

        # if helper comes back with false
        if not expire_days:
            expire_days = "5"

        if user:
            self.set_secure_cookie("user", tornado.escape.json_encode(user), expires_days=int(expire_days))
        else:
            self.clear_cookie("user")

    def get(self, page=None):

        self.clear_cookie("user")
        self.clear_cookie("user_data")

        error = bleach.clean(self.get_argument('error', "Invalid Login!"))

        page_data = {
            'version': helper.get_version_string(),
            'error': error
            }

        # sensible defaults
        template = "public/404.html"

        if page == "login":
            template = "public/login.html"

        elif page == 404:
            template = "public/404.html"

        elif page == "error":
            template = "public/error.html"

        # if we have no page, let's go to login
        else:
            self.redirect('/public/login')

        self.render(template, data=page_data)

    def post(self, page=None):

        if page == 'login':
            next_page = "/public/login"

            entered_username = bleach.clean(self.get_argument('username'))
            entered_password = bleach.clean(self.get_argument('password'))

            user_data = Users.get_or_none(fn.Lower(Users.username) == entered_username.lower())

            # if we don't have a user
            if not user_data:
                next_page = "/public/login?error=Login_Failed"
                self.redirect(next_page)
                return False

            # if they are disabled
            if not user_data.enabled:
                next_page = "/public/login?error=Login_Failed"
                self.redirect(next_page)
                return False

            login_result = helper.verify_pass(entered_password, user_data.password)

            # Valid Login
            if login_result:
                self.set_current_user(entered_username)
                logger.info("User: {} Logged in from IP: {}".format(user_data, self.get_remote_ip()))

                # record this login
                Users.update({
                    Users.last_ip: self.get_remote_ip(),
                    Users.last_login: helper.get_time_as_string()
                }).where(Users.username == entered_username).execute()

                cookie_data = {
                    "username": user_data.username,
                    "user_id": user_data.id,
                    "account_type": user_data.allowed_servers,

                }

                self.set_secure_cookie('user_data', json.dumps(cookie_data))

                next_page = "/panel/dashboard"
                self.redirect(next_page)

            self.redirect("/public/login")

