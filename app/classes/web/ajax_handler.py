import json
import logging
import tornado.web
import tornado.escape
import bleach

from app.classes.shared.console import console
from app.classes.shared.models import Users, installer
from app.classes.web.base_handler import BaseHandler
from app.classes.shared.controller import controller
from app.classes.shared.models import db_helper
from app.classes.shared.helpers import helper

logger = logging.getLogger(__name__)


class AjaxHandler(BaseHandler):

    def render_page(self, template, page_data):
        self.render(
            template,
            data=page_data
        )

    @tornado.web.authenticated
    def get(self, page):
        user_data = json.loads(self.get_secure_cookie("user_data"))
        error = bleach.clean(self.get_argument('error', "WTF Error!"))

        template = "panel/denied.html"

        page_data = {
            'user_data': user_data,
            'error': error
        }

        if page == "error":
            template = "public/error.html"
            self.render_page(template, page_data)

        elif page == 'server_log':
            server_id = self.get_argument('id', None)
            full_log = self.get_argument('full', False)

            if server_id is None:
                logger.warning("Server ID not found in server_log ajax call")
                self.redirect("/panel/error?error=Server ID Not Found")
                return False

            server_id = bleach.clean(server_id)

            server_data = db_helper.get_server_data_by_id(server_id)
            if not server_data:
                logger.warning("Server Data not found in server_log ajax call")
                self.redirect("/panel/error?error=Server ID Not Found")

            if server_data['log_path']:
                logger.warning("Server ID not found in server_log ajax call")

            if full_log:
                log_lines = helper.get_setting('max_log_lines')
            else:
                log_lines = helper.get_setting('virtual_terminal_lines')

            data = helper.tail_file(server_data['log_path'], log_lines)

            for d in data:
                try:
                    line = helper.log_colors(d)
                    self.write('{}<br />'.format(line))
                    # self.write(d.encode("utf-8"))

                except Exception as e:
                    logger.warning("Skipping Log Line due to error: {}".format(e))
                    pass

    def post(self, page):
        user_data = json.loads(self.get_secure_cookie("user_data"))
        error = bleach.clean(self.get_argument('error', "WTF Error!"))

        page_data = {
            'user_data': user_data,
            'error': error
        }

        if page == "send_command":
            command = bleach.clean(self.get_body_argument('command', default=None, strip=True))
            server_id = bleach.clean(self.get_argument('id'))

            if server_id is None:
                logger.warning("Server ID not found in send_command ajax call")

            srv_obj = controller.get_server_obj(server_id)

            if command:
                if srv_obj.check_running():
                    srv_obj.send_command(command)

