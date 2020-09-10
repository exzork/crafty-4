import sys
import json
import logging

from app.classes.shared.console import console
from app.classes.web.base_handler import BaseHandler
from app.classes.shared.controller import controller
from app.classes.shared.models import db_helper, Servers
from app.classes.minecraft.serverjars import server_jar_obj
from app.classes.minecraft.stats import stats
from app.classes.shared.helpers import helper


logger = logging.getLogger(__name__)

try:
    import tornado.web
    import tornado.escape
    import bleach

except ModuleNotFoundError as e:
    logger.critical("Import Error: Unable to load {} module".format(e, e.name))
    console.critical("Import Error: Unable to load {} module".format(e, e.name))
    sys.exit(1)


class ServerHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self, page):
        # name = tornado.escape.json_decode(self.current_user)
        user_data = json.loads(self.get_secure_cookie("user_data"))

        template = "public/404.html"

        defined_servers = controller.list_defined_servers()

        page_data = {
            'version_data': "version_data_here",
            'user_data': user_data,
            'server_stats': {
                'total': len(controller.list_defined_servers()),
                'running': len(controller.list_running_servers()),
                'stopped': (len(controller.list_defined_servers()) - len(controller.list_running_servers()))
            },
            'hosts_data': db_helper.get_latest_hosts_stats(),
            'menu_servers': defined_servers,
            'show_contribute': helper.get_setting("show_contribute_link", True)
        }

        if page == "step1":

            page_data['server_types'] = server_jar_obj.get_serverjar_data()
            template = "server/wizard.html"

        self.render(
            template,
            data=page_data
        )

    @tornado.web.authenticated
    def post(self, page):

        user_data = json.loads(self.get_secure_cookie("user_data"))

        template = "public/404.html"
        page_data = {
            'version_data': "version_data_here",
            'user_data': user_data,
            'show_contribute': helper.get_setting("show_contribute_link", True)
        }

        if page == "command":
            server_id = bleach.clean(self.get_argument("id", None))
            command = bleach.clean(self.get_argument("command", None))

            if server_id is not None:
                db_helper.send_command(user_data['user_id'], server_id, self.get_remote_ip(), command)

        if page == "step1":

            server = bleach.clean(self.get_argument('server', ''))
            server_name = bleach.clean(self.get_argument('server_name', ''))
            min_mem = bleach.clean(self.get_argument('min_memory', ''))
            max_mem = bleach.clean(self.get_argument('max_memory', ''))
            port = bleach.clean(self.get_argument('port', ''))

            server_parts = server.split("|")

            # todo: add server type check here and call the correct server add functions if not a jar
            new_server_id = controller.create_jar_server(server_parts[0], server_parts[1], server_name, min_mem, max_mem, port)

            if new_server_id:
                db_helper.add_to_audit_log(user_data['user_id'],
                                           "Created server {} named {}".format(server, server_name),
                                           new_server_id,
                                           self.get_remote_ip())
                stats.record_stats()
                self.redirect("/panel/dashboard")

        self.render(
            template,
            data=page_data
        )