import sys
import json
import logging
import os
import shutil

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
            'version_data': helper.get_version_string(),
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
                if command == "clone_server":
                    def is_name_used(name):
                        for server in db_helper.get_all_defined_servers():
                            if server['server_name'] == name:
                                return True
                        return False
                    
                    server_data = db_helper.get_server_data_by_id(server_id)
                    server_uuid = server_data.get('server_uuid')
                    new_server_name = server_data.get('server_name') + " (Copy)"

                    name_counter = 1
                    while is_name_used(new_server_name):
                        name_counter += 1
                        new_server_name = server_data.get('server_name') + " (Copy {})".format(name_counter)

                    console.debug('new_server_name: "{}"'.format(new_server_name))

                    new_server_uuid = helper.create_uuid()
                    while os.path.exists(os.path.join(helper.servers_dir, new_server_uuid)):
                        new_server_uuid = helper.create_uuid()
                    new_server_path = os.path.join(helper.servers_dir, new_server_uuid)

                    # copy the old server
                    shutil.copytree(server_data.get('path'), new_server_path)

                    # TODO get old server DB data to individual variables
                    stop_command = server_data.get('stop_command')
                    new_server_command = str(server_data.get('execution_command')).replace(server_uuid, new_server_uuid)
                    new_executable = server_data.get('executable')
                    new_server_log_file = str(server_data.get('log_path')).replace(server_uuid, new_server_uuid)
                    auto_start = server_data.get('auto_start')
                    auto_start_delay = server_data.get('auto_start_delay')
                    crash_detection = server_data.get('crash_detection')
                    server_port = server_data.get('server_port')


                    # TODO create the server on the DB side

                    Servers.insert({
                        Servers.server_name: new_server_name,
                        Servers.server_uuid: new_server_uuid,
                        Servers.path: new_server_path,
                        Servers.executable: new_executable,
                        Servers.execution_command: new_server_command,
                        Servers.auto_start: auto_start,
                        Servers.auto_start_delay: auto_start_delay,
                        Servers.crash_detection: crash_detection,
                        Servers.log_path: new_server_log_file,
                        Servers.server_port: server_port,
                        Servers.stop_command: stop_command
                    }).execute()

                    controller.init_all_servers()
                    console.debug('initted all servers')

                    return
                
                db_helper.send_command(user_data['user_id'], server_id, self.get_remote_ip(), command)

        if page == "step1":

            server = bleach.clean(self.get_argument('server', ''))
            server_name = bleach.clean(self.get_argument('server_name', ''))
            min_mem = bleach.clean(self.get_argument('min_memory', ''))
            max_mem = bleach.clean(self.get_argument('max_memory', ''))
            port = bleach.clean(self.get_argument('port', ''))
            import_type = bleach.clean(self.get_argument('create_type', ''))
            import_server_path = bleach.clean(self.get_argument('server_path', ''))
            import_server_jar = bleach.clean(self.get_argument('server_jar', ''))
            server_parts = server.split("|")

            if import_type == 'import_jar':
                good_path = controller.verify_jar_server(import_server_path, import_server_jar)

                if not good_path:
                    self.redirect("/panel/error?error=Server path or Server Jar not found!")
                    return False

                new_server_id = controller.import_jar_server(server_name, import_server_path,import_server_jar, min_mem, max_mem, port)
            elif import_type == 'import_zip':
                good_path = controller.verify_zip_server(import_server_path)
                if not good_path:
                    self.redirect("/panel/error?error=Zip file not found!")
                    return False

                new_server_id = controller.import_zip_server(server_name, import_server_path,import_server_jar, min_mem, max_mem, port)
                if new_server_id == "false":
                    self.redirect("/panel/error?error=ZIP file not accessible! You can fix this permissions issue with sudo chown -R crafty:crafty {} And sudo chmod 2775 -R {}".format(import_server_path, import_server_path))
                    return False
            else:
                # todo: add server type check here and call the correct server add functions if not a jar
                new_server_id = controller.create_jar_server(server_parts[0], server_parts[1], server_name, min_mem, max_mem, port)

            if new_server_id:
                db_helper.add_to_audit_log(user_data['user_id'],
                                           "Created server {} named {}".format(server, server_name),
                                           new_server_id,
                                           self.get_remote_ip())
            else:
                logger.error("Unable to create server")
                console.error("Unable to create server")

            stats.record_stats()
            self.redirect("/panel/dashboard")

        self.render(
            template,
            data=page_data
        )