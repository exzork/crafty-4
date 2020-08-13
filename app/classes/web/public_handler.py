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

        # print(page)

        if page is None:
            self.redirect("public/login")

        error = bleach.clean(self.get_argument('error', ""))

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

    def post(self, page=None):

        if page == 'login':
            next_page = "/public/login"

            entered_email = bleach.clean(self.get_argument('email'))
            entered_password = bleach.clean(self.get_argument('password'))

            user_data = Users.get_or_none(Users.email_address == entered_email)

            # if we already have a user with this email...
            if not user_data:
                next_page = "/public/login?error=Login_Failed"
                self.redirect(next_page)
                return False

            login_result = helper.verify_pass(entered_password, user_data.password)

            # Valid Login
            if login_result:
                self.set_current_user(entered_email)
                logger.info("User: {} Logged in from IP: {}".format(entered_email, self.get_remote_ip()))

                Users.update({
                    Users.last_ip: self.get_remote_ip()
                }).execute()

                cookie_data = {
                    "user_email": user_data.email_address,
                    "user_id": user_data,
                    "account_type": str(user_data.account_type).upper(),

                }

                self.set_secure_cookie('user_data', json.dumps(cookie_data))

                next_page = "/pro/dashboard"
                self.redirect(next_page)
        else:
            self.redirect("/public/login")

