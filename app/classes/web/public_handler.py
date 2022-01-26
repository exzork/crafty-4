import sys
import logging

from app.classes.shared.authentication import authentication
from app.classes.shared.helpers import helper
from app.classes.shared.console import console
from app.classes.shared.main_models import fn

from app.classes.models.users import Users
from app.classes.web.base_handler import BaseHandler

logger = logging.getLogger(__name__)

try:
    import bleach

except ModuleNotFoundError as e:
    logger.critical(f"Import Error: Unable to load {e.name} module", exc_info=True)
    console.critical(f"Import Error: Unable to load {e.name} module")
    sys.exit(1)

class PublicHandler(BaseHandler):

    def set_current_user(self, user_id: str = None):

        expire_days = helper.get_setting('cookie_expire')

        # if helper comes back with false
        if not expire_days:
            expire_days = "5"

        if user_id is not None:
            self.set_cookie("token", authentication.generate(user_id), expires_days=int(expire_days))
        else:
            self.clear_cookie("user")

    def get(self, page=None):

        error = bleach.clean(self.get_argument('error', "Invalid Login!"))
        error_msg = bleach.clean(self.get_argument('error_msg', ''))

        page_data = {'version': helper.get_version_string(), 'error': error, 'lang': helper.get_setting('language')}

        # sensible defaults
        template = "public/404.html"

        if page == "login":
            template = "public/login.html"

        elif page == 404:
            template = "public/404.html"

        elif page == "error":
            template = "public/error.html"

        elif page == "logout":
            self.clear_cookie("user")
            self.clear_cookie("user_data")
            self.redirect('/public/login')
            return

        # if we have no page, let's go to login
        else:
            self.redirect('/public/login')
            return

        self.render(
            template,
            data=page_data,
            translate=self.translator.translate,
            error_msg = error_msg
        )

    def post(self, page=None):

        if page == 'login':
            next_page = "/public/login"

            entered_username = bleach.clean(self.get_argument('username'))
            entered_password = bleach.clean(self.get_argument('password'))

            # pylint: disable=no-member
            user_data = Users.get_or_none(fn.Lower(Users.username) == entered_username.lower())


            # if we don't have a user
            if not user_data:
                error_msg = "Incorrect username or password. Please try again."
                self.clear_cookie("user")
                self.clear_cookie("user_data")
                self.redirect(f'/public/login?error_msg={error_msg}')
                return

            # if they are disabled
            if not user_data.enabled:
                error_msg = "User account disabled. Please contact your system administrator for more info."
                self.clear_cookie("user")
                self.clear_cookie("user_data")
                self.redirect(f'/public/login?error_msg={error_msg}')
                return

            login_result = helper.verify_pass(entered_password, user_data.password)

            # Valid Login
            if login_result:
                self.set_current_user(user_data.user_id)
                logger.info(f"User: {user_data} Logged in from IP: {self.get_remote_ip()}")

                # record this login
                q = Users.select().where(Users.username == entered_username.lower()).get()
                q.last_ip = self.get_remote_ip()
                q.last_login = helper.get_time_as_string()
                q.save()

                # log this login
                self.controller.management.add_to_audit_log(user_data.user_id, "Logged in", 0, self.get_remote_ip())

                next_page = "/panel/dashboard"
                self.redirect(next_page)
            else:
                self.clear_cookie("user")
                self.clear_cookie("user_data")
                error_msg = "Inncorrect username or password. Please try again."
                # log this failed login attempt
                self.controller.management.add_to_audit_log(user_data.user_id, "Tried to log in", 0, self.get_remote_ip())
                self.redirect(f'/public/login?error_msg={error_msg}')
        else:
            self.redirect("/public/login")
