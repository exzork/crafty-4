import json
import logging
import tornado.web
import tornado.escape
import bleach

from app.classes.shared.console import console
from app.classes.shared.models import Users, installer
from app.classes.web.base_handler import BaseHandler
from app.classes.shared.controller import controller
from app.classes.shared.models import db_helper, Servers
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
            # todo: make this actually pull and compare version data
            'update_available': False,
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

        elif page == 'file_edit':
            template = "panel/file_edit.html"

        elif page == "remove_server":
            server_id = self.get_argument('id', None)
            server_data = controller.get_server_data(server_id)
            server_name = server_data['server_name']

            db_helper.add_to_audit_log(user_data['user_id'],
                                       "Deleted server {} named {}".format(server_id, server_name),
                                       server_id,
                                       self.get_remote_ip())

            controller.remove_server(server_id)
            self.redirect("/panel/dashboard")
            return

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

            valid_subpages = ['term', 'logs', 'config', 'files']

            if subpage not in valid_subpages:
                console.debug('not a valid subpage')
                subpage = 'term'
            console.debug('Subpage: "{}"'.format(subpage))

            # server_data isn't needed since the server_stats also pulls server data
            # page_data['server_data'] = db_helper.get_server_data_by_id(server_id)
            page_data['server_stats'] = db_helper.get_server_stats_by_id(server_id)

            # template = "panel/server_details.html"
            template = "panel/server_{subpage}.html".format(subpage=subpage)


        self.render(
            template,
            data=page_data
        )

    @tornado.web.authenticated
    def post(self, page):

        if page == 'server_detail':
            server_id = self.get_argument('id', None)
            server_name = self.get_argument('server_name', None)
            server_path = self.get_argument('server_path', None)
            log_path = self.get_argument('log_path', None)
            executable = self.get_argument('executable', None)
            execution_command = self.get_argument('execution_command', None)
            stop_command = self.get_argument('stop_command', None)
            auto_start_delay = self.get_argument('auto_start_delay', '10')
            server_ip = self.get_argument('server_ip', None)
            server_port = self.get_argument('server_port', None)
            auto_start = int(float(self.get_argument('auto_start', '0')))
            crash_detection = int(float(self.get_argument('crash_detection', '0')))
            subpage = self.get_argument('subpage', None)

            if server_id is None:
                self.redirect("/panel/error?error=Invalid Server ID")
                return False
            else:
                server_id = bleach.clean(server_id)

                # does this server id exist?
                if not db_helper.server_id_exists(server_id):
                    self.redirect("/panel/error?error=Invalid Server ID")
                    return False

            Servers.update({
                Servers.server_name: server_name,
                Servers.path: server_path,
                Servers.log_path: log_path,
                Servers.executable: executable,
                Servers.execution_command: execution_command,
                Servers.stop_command: stop_command,
                Servers.auto_start_delay: auto_start_delay,
                Servers.server_ip: server_ip,
                Servers.server_port: server_port,
                Servers.auto_start: auto_start,
                Servers.crash_detection: crash_detection,
            }).where(Servers.server_id == server_id).execute()

            controller.refresh_server_settings(server_id)

            user_data = json.loads(self.get_secure_cookie("user_data"))

            db_helper.add_to_audit_log(user_data['user_id'],
                                       "Edited server {} named {}".format(server_id, server_name),
                                       server_id,
                                       self.get_remote_ip())

            self.redirect("/panel/server_detail?id={}&subpage=config".format(server_id))
