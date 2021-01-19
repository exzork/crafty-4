import json
import logging
import tornado.web
import tornado.escape
import bleach
import time
import datetime

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

        now = time.time()
        formatted_time = str(datetime.datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S'))

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
            'error': error,
            'time': formatted_time
        }

        # if no servers defined, let's go to the build server area
        if page_data['server_stats']['total'] == 0 and page != "error":
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

        elif page == 'panel_config':
            page_data['users'] = db_helper.get_all_users()
            page_data['roles'] = db_helper.get_all_roles()
            exec_user = db_helper.get_user(user_data['user_id'])
            for user in page_data['users']:
                if user.user_id != exec_user['user_id']:
                    user.api_token = "********"
            template = "panel/panel_config.html"

        elif page == "add_user":
            page_data['new_user'] = True
            page_data['user'] = {}
            page_data['user']['username'] = ""
            page_data['user']['user_id'] = -1
            page_data['user']['enabled'] = True
            page_data['user']['superuser'] = False
            page_data['user']['api_token'] = "N/A"
            page_data['user']['created'] = "N/A"
            page_data['user']['last_login'] = "N/A"
            page_data['user']['last_ip'] = "N/A"
            page_data['role']['last_update'] = "N/A"
            page_data['user']['roles'] = set()
            page_data['user']['servers'] = set()

            exec_user = db_helper.get_user(user_data['user_id'])

            if not exec_user['superuser']:
                self.redirect("/panel/error?error=Unauthorized access: not superuser")
                return False

            page_data['roles_all'] = db_helper.get_all_roles()
            page_data['servers_all'] = controller.list_defined_servers()
            template = "panel/panel_edit_user.html"

        elif page == "edit_user":
            page_data['new_user'] = False
            user_id = self.get_argument('id', None)
            page_data['user'] = db_helper.get_user(user_id)
            page_data['roles_all'] = db_helper.get_all_roles()
            page_data['servers_all'] = controller.list_defined_servers()

            exec_user = db_helper.get_user(user_data['user_id'])

            if not exec_user['superuser']:
                self.redirect("/panel/error?error=Unauthorized access: not superuser")
                return False
            elif user_id is None:
                self.redirect("/panel/error?error=Invalid User ID")
                return False

            if exec_user['user_id'] != page_data['user']['user_id']:
                page_data['user']['api_token'] = "********"
            template = "panel/panel_edit_user.html"

        elif page == "remove_user":
            user_id = bleach.clean(self.get_argument('id', None))

            user_data = json.loads(self.get_secure_cookie("user_data"))
            exec_user = db_helper.get_user(user_data['user_id'])

            if not exec_user['superuser']:
                self.redirect("/panel/error?error=Unauthorized access: not superuser")
                return False
            elif user_id is None:
                self.redirect("/panel/error?error=Invalid User ID")
                return False
            else:
                # does this user id exist?
                target_user = db_helper.get_user(user_id)
                if not target_user:
                    self.redirect("/panel/error?error=Invalid User ID")
                    return False
                elif target_user['superuser']:
                    self.redirect("/panel/error?error=Cannot remove a superuser")
                    return False

            db_helper.remove_user(user_id)

            db_helper.add_to_audit_log(exec_user['user_id'],
                                       "Removed user {} (UID:{})".format(target_user['username'], user_id),
                                       server_id=0,
                                       source_ip=self.get_remote_ip())
            self.redirect("/panel/panel_config")

        elif page == "add_role":
            page_data['new_role'] = True
            page_data['role'] = {}
            page_data['role']['role_name'] = ""
            page_data['role']['role_id'] = -1
            page_data['role']['created'] = "N/A"
            page_data['role']['last_update'] = "N/A"
            page_data['role']['servers'] = set()

            exec_user = db_helper.get_user(user_data['user_id'])

            if not exec_user['superuser']:
                self.redirect("/panel/error?error=Unauthorized access: not superuser")
                return False

            page_data['servers_all'] = controller.list_defined_servers()
            template = "panel/panel_edit_role.html"

        elif page == "edit_role":
            page_data['new_role'] = False
            role_id = self.get_argument('id', None)
            page_data['role'] = db_helper.get_role(role_id)
            page_data['servers_all'] = controller.list_defined_servers()

            exec_user = db_helper.get_user(user_data['user_id'])

            if not exec_user['superuser']:
                self.redirect("/panel/error?error=Unauthorized access: not superuser")
                return False
            elif role_id is None:
                self.redirect("/panel/error?error=Invalid Role ID")
                return False

            template = "panel/panel_edit_role.html"

        elif page == "remove_role":
            role_id = bleach.clean(self.get_argument('id', None))

            user_data = json.loads(self.get_secure_cookie("user_data"))
            exec_user = db_helper.get_user(user_data['user_id'])

            if not exec_user['superuser']:
                self.redirect("/panel/error?error=Unauthorized access: not superuser")
                return False
            elif role_id is None:
                self.redirect("/panel/error?error=Invalid Role ID")
                return False
            else:
                # does this user id exist?
                target_role = db_helper.get_user(role_id)
                if not target_role:
                    self.redirect("/panel/error?error=Invalid Role ID")
                    return False

            db_helper.remove_role(role_id)

            db_helper.add_to_audit_log(exec_user['user_id'],
                                       "Removed role {} (RID:{})".format(target_role['role_name'], role_id),
                                       server_id=0,
                                       source_ip=self.get_remote_ip())
            self.redirect("/panel/panel_config")

        elif page == "activity_logs":
            page_data['audit_logs'] = db_helper.get_actity_log()

            template = "panel/activity_logs.html"

        self.render(
            template,
            data=page_data,
            time=time,
            utc_offset=(time.timezone * -1 / 60 / 60),
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

            user_data = json.loads(self.get_secure_cookie("user_data"))
            exec_user = db_helper.get_user(user_data['user_id'])

            if not exec_user.superuser:
                self.redirect("/panel/error?error=Unauthorized access: not superuser")
                return False
            elif server_id is None:
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

            db_helper.add_to_audit_log(user_data['user_id'],
                                       "Edited server {} named {}".format(server_id, server_name),
                                       server_id,
                                       self.get_remote_ip())

            self.redirect("/panel/server_detail?id={}&subpage=config".format(server_id))

        elif page == "edit_user":
            user_id = bleach.clean(self.get_argument('id', None))
            username = bleach.clean(self.get_argument('username', None))
            password0 = bleach.clean(self.get_argument('password0', None))
            password1 = bleach.clean(self.get_argument('password1', None))
            enabled = int(float(bleach.clean(self.get_argument('enabled'), '0')))
            regen_api = int(float(bleach.clean(self.get_argument('regen_api', '0'))))

            user_data = json.loads(self.get_secure_cookie("user_data"))
            exec_user = db_helper.get_user(user_data['user_id'])

            if not exec_user['superuser']:
                self.redirect("/panel/error?error=Unauthorized access: not superuser")
                return False
            elif username is None or username == "":
                self.redirect("/panel/error?error=Invalid username")
                return False
            elif user_id is None:
                self.redirect("/panel/error?error=Invalid User ID")
                return False
            else:
                # does this user id exist?
                if not db_helper.user_id_exists(user_id):
                    self.redirect("/panel/error?error=Invalid User ID")
                    return False

            if password0 != password1:
                self.redirect("/panel/error?error=Passwords must match")
                return False

            roles = set()
            for role in db_helper.get_all_roles():
                argument = int(float(
                    bleach.clean(
                        self.get_argument('role_{}_membership'.format(role.role_id), '0')
                    )
                ))
                if argument:
                    roles.add(role.role_id)

            servers = set()
            for server in controller.list_defined_servers():
                argument = int(float(
                    bleach.clean(
                        self.get_argument('server_{}_access'.format(server['server_id']), '0')
                    )
                ))
                if argument:
                    servers.add(server['server_id'])

            user_data = {
                "username": username,
                "password": password0,
                "enabled": enabled,
                "regen_api": regen_api,
                "roles": roles,
                "servers": servers
            }
            db_helper.update_user(user_id, user_data=user_data)

            db_helper.add_to_audit_log(exec_user['user_id'],
                                       "Edited user {} (UID:{}) with roles {} and servers {}".format(username, user_id, roles, servers),
                                       server_id=0,
                                       source_ip=self.get_remote_ip())
            self.redirect("/panel/panel_config")


        elif page == "add_user":
            username = bleach.clean(self.get_argument('username', None))
            password0 = bleach.clean(self.get_argument('password0', None))
            password1 = bleach.clean(self.get_argument('password1', None))
            enabled = int(float(bleach.clean(self.get_argument('enabled'), '0')))

            user_data = json.loads(self.get_secure_cookie("user_data"))
            exec_user = db_helper.get_user(user_data['user_id'])
            if not exec_user['superuser']:
                self.redirect("/panel/error?error=Unauthorized access: not superuser")
                return False
            elif username is None or username == "":
                self.redirect("/panel/error?error=Invalid username")
                return False
            else:
                # does this user id exist?
                if db_helper.get_userid_by_name(username) is not None:
                    self.redirect("/panel/error?error=User exists")
                    return False

            if password0 != password1:
                self.redirect("/panel/error?error=Passwords must match")
                return False

            roles = set()
            for role in db_helper.get_all_roles():
                argument = int(float(
                    bleach.clean(
                        self.get_argument('role_{}_membership'.format(role.role_id), '0')
                    )
                ))
                if argument:
                    roles.add(role['role_id'])

            servers = set()
            for server in controller.list_defined_servers():
                argument = int(float(
                    bleach.clean(
                        self.get_argument('server_{}_access'.format(server['server_id']), '0')
                    )
                ))
                if argument:
                    servers.add(server['server_id'])

            user_id = db_helper.add_user(username, password=password0, enabled=enabled)
            db_helper.update_user(user_id, {"roles":roles, "servers": servers})

            db_helper.add_to_audit_log(exec_user['user_id'],
                                       "Added user {} (UID:{})".format(username, user_id),
                                       server_id=0,
                                       source_ip=self.get_remote_ip())
            db_helper.add_to_audit_log(exec_user['user_id'],
                                       "Edited user {} (UID:{}) with roles {} and servers {}".format(username, user_id, roles, servers),
                                       server_id=0,
                                       source_ip=self.get_remote_ip())
            self.redirect("/panel/panel_config")

        elif page == "edit_role":
            role_id = bleach.clean(self.get_argument('id', None))
            role_name = bleach.clean(self.get_argument('role_name', None))

            user_data = json.loads(self.get_secure_cookie("user_data"))
            exec_user = db_helper.get_user(user_data['user_id'])

            if not exec_user['superuser']:
                self.redirect("/panel/error?error=Unauthorized access: not superuser")
                return False
            elif role_name is None or role_name == "":
                self.redirect("/panel/error?error=Invalid username")
                return False
            elif role_id is None:
                self.redirect("/panel/error?error=Invalid Role ID")
                return False
            else:
                # does this user id exist?
                if not db_helper.role_id_exists(role_id):
                    self.redirect("/panel/error?error=Invalid Role ID")
                    return False

            servers = set()
            for server in controller.list_defined_servers():
                argument = int(float(
                    bleach.clean(
                        self.get_argument('server_{}_access'.format(server['server_id']), '0')
                    )
                ))
                if argument:
                    servers.add(server['server_id'])

            role_data = {
                "role_name": role_name,
                "servers": servers
            }
            db_helper.update_role(role_id, role_data=role_data)

            db_helper.add_to_audit_log(exec_user['user_id'],
                                       "Edited role {} (RID:{}) with servers {}".format(role_name, role_id, servers),
                                       server_id=0,
                                       source_ip=self.get_remote_ip())
            self.redirect("/panel/panel_config")


        elif page == "add_role":
            role_name = bleach.clean(self.get_argument('role_name', None))

            user_data = json.loads(self.get_secure_cookie("user_data"))
            exec_user = db_helper.get_user(user_data['user_id'])
            if not exec_user['superuser']:
                self.redirect("/panel/error?error=Unauthorized access: not superuser")
                return False
            elif role_name is None or role_name == "":
                self.redirect("/panel/error?error=Invalid role name")
                return False
            else:
                # does this user id exist?
                if db_helper.get_roleid_by_name(role_name) is not None:
                    self.redirect("/panel/error?error=Role exists")
                    return False

            servers = set()
            for server in controller.list_defined_servers():
                argument = int(float(
                    bleach.clean(
                        self.get_argument('server_{}_access'.format(server['server_id']), '0')
                    )
                ))
                if argument:
                    servers.add(server['server_id'])

            role_id = db_helper.add_role(role_name)
            db_helper.update_role(role_id, {"servers": servers})

            db_helper.add_to_audit_log(exec_user['user_id'],
                                       "Added role {} (RID:{})".format(role_name, role_id),
                                       server_id=0,
                                       source_ip=self.get_remote_ip())
            db_helper.add_to_audit_log(exec_user['user_id'],
                                       "Edited role {} (RID:{}) with servers {}".format(role_name, role_id, servers),
                                       server_id=0,
                                       source_ip=self.get_remote_ip())
            self.redirect("/panel/panel_config")