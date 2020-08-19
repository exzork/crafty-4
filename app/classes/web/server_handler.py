import json
import logging
import tornado.web
import tornado.escape
import bleach

from app.classes.shared.console import console
from app.classes.shared.models import Users, installer
from app.classes.web.base_handler import BaseHandler
from app.classes.minecraft.controller import controller
from app.classes.shared.models import db_helper


logger = logging.getLogger(__name__)


class ServerHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self, page):
        # name = tornado.escape.json_decode(self.current_user)
        user_data = json.loads(self.get_secure_cookie("user_data"))

        template = "public/404.html"


        page_data = {
            'version_data': "version_data_here",
            'user_data': user_data,
            'server_stats': {
                'total': len(controller.list_defined_servers()),
                'running': len(controller.list_running_servers()),
                'stopped': (len(controller.list_defined_servers()) - len(controller.list_running_servers()))
            },
            'hosts_data': db_helper.get_latest_hosts_stats()

        }
        # print(page_data['hosts_data'])

        print(page)


        self.render(
            template,
            data=page_data
        )