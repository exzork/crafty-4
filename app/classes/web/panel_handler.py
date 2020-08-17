import json
import logging
import tornado.web
import tornado.escape
import bleach

from app.classes.shared.console import console
from app.classes.shared.models import Users, installer
from app.classes.web.base_handler import BaseHandler
from app.classes.minecraft.controller import controller

logger = logging.getLogger(__name__)


class PanelHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self, page):
        # name = tornado.escape.json_decode(self.current_user)
        user_data = json.loads(self.get_secure_cookie("user_data"))

        template = "panel/denied.html"

        page_data = {
            'version_data': "version_data_here",
            'user_data': user_data
        }

        servers = controller.list_defined_servers()

        if page == 'unauthorized':
            template = "panel/denied.html"

        elif page == 'dashboard':
            template = "panel/dashboard.html"

        self.render(
            template,
            data=page_data
        )