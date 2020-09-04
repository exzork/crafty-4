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


class PanelHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self, page):
        user_data = json.loads(self.get_secure_cookie("user_data"))
        error = bleach.clean(self.get_argument('error', "WTF Error!"))

        template = "panel/denied.html"

        defined_servers = controller.list_defined_servers()

        page_data = {
            'version_data': helper.get_version_string(),
            'user_data': user_data,
            'server_stats': {
                'total': len(defined_servers),
                'running': len(controller.list_running_servers()),
                'stopped': (len(controller.list_defined_servers()) - len(controller.list_running_servers()))
            },
            'menu_servers': defined_servers,
            'hosts_data': db_helper.get_latest_hosts_stats(),
            'show_contribute': helper.get_setting("show_contribute_link", True),
            'error': error
        }

        # if no servers defined, let's go to the build server area
        if page_data['server_stats']['total'] == 0:
            self.set_status(301)
            self.redirect("/server/step1")
            return False

        if page == 'unauthorized':
            template = "panel/denied.html"

        elif page == "error":
            template = "public/error.html"

        elif page == 'credits':
            template = "panel/credits.html"

        elif page == 'contribute':
            template = "panel/contribute.html"

        elif page == 'dashboard':
            page_data['servers'] = db_helper.get_all_servers_stats()

            for s in page_data['servers']:
                try:
                    data = json.loads(s['int_ping_results'])
                    s['int_ping_results'] = data
                except:
                    pass

            template = "panel/dashboard.html"

        elif page == 'server_detail':
            server_id = self.get_argument('id', None)
            subpage = bleach.clean(self.get_argument('subpage', ""))

            if server_id is None:
                self.redirect("/panel/error?error=Invalid Server ID")
                return False
            else:
                server_id = bleach.clean(server_id)

                # does this server id exist?
                if not db_helper.server_id_exists(server_id):
                    self.redirect("/panel/error?error=Invalid Server ID")
                    return False

            valid_subpages = ['term', 'logs']

            if subpage not in valid_subpages:
                subpage = 'term'

            # server_data isn't needed since the server_stats also pulls server data
            # page_data['server_data'] = db_helper.get_server_data_by_id(server_id)
            page_data['server_stats'] = db_helper.get_server_stats_by_id(server_id)

            # template = "panel/server_details.html"
            template = "panel/server_{subpage}.html".format(subpage=subpage)


        self.render(
            template,
            data=page_data
        )
