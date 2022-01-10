from app.classes.shared.translation import Translation
import json
import logging
import tornado.web
import tornado.escape
import bleach
import time
import datetime
import os

from tornado import iostream
from tornado.ioloop import IOLoop
from app.classes.shared.console import console
from app.classes.shared.main_models import Users, installer

from app.classes.web.base_handler import BaseHandler

from app.classes.models.servers import Servers
from app.classes.models.server_permissions import Enum_Permissions_Server, Permissions_Servers
from app.classes.models.crafty_permissions import Enum_Permissions_Crafty, Permissions_Crafty
from app.classes.models.management import management_helper

from app.classes.shared.helpers import helper

logger = logging.getLogger(__name__)


class PanelHandler(BaseHandler):

    # Server fetching, spawned asynchronously 
    # TODO: Make the related front-end elements update with AJAX
    def fetch_server_data(self, page_data):
        total_players = 0
        for server in page_data['servers']:
            total_players += len(self.controller.stats.get_server_players(server['server_data']['server_id']))
        page_data['num_players'] = total_players

        for s in page_data['servers']:
            try:
                data = json.loads(s['int_ping_results'])
                s['int_ping_results'] = data
            except Exception as e:
                logger.error("Failed server data for page with error: {} ".format(e))
        
        return page_data


    @tornado.web.authenticated
    async def get(self, page):
        error = bleach.clean(self.get_argument('error', "WTF Error!"))

        template = "panel/denied.html"

        now = time.time()
        formatted_time = str(datetime.datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S'))

        exec_user_data = json.loads(self.get_secure_cookie("user_data"))
        exec_user_id = exec_user_data['user_id']
        exec_user = self.controller.users.get_user_by_id(exec_user_id)

        exec_user_role = set()
        if exec_user['superuser'] == 1:
            defined_servers = self.controller.list_defined_servers()
            exec_user_role.add("Super User")
            exec_user_crafty_permissions = self.controller.crafty_perms.list_defined_crafty_permissions()
        else:
            exec_user_crafty_permissions = self.controller.crafty_perms.get_crafty_permissions_list(exec_user_id)
            logger.debug(exec_user['roles'])
            for r in exec_user['roles']:
                role = self.controller.roles.get_role(r)
                exec_user_role.add(role['role_name'])
            defined_servers = self.controller.servers.get_authorized_servers(exec_user_id)

        page_data = {
            # todo: make this actually pull and compare version data
            'update_available': False,
            'serverTZ': time.tzname,
            'version_data': helper.get_version_string(),
            'user_data': exec_user_data,
            'user_role' : exec_user_role,
            'user_crafty_permissions' : exec_user_crafty_permissions,
            'crafty_permissions': {
                'Server_Creation': Enum_Permissions_Crafty.Server_Creation,
                'User_Config': Enum_Permissions_Crafty.User_Config,
                'Roles_Config': Enum_Permissions_Crafty.Roles_Config,
            },
            'server_stats': {
                'total': len(defined_servers),
                'running': len(self.controller.list_running_servers()),
                'stopped': (len(self.controller.list_defined_servers()) - len(self.controller.list_running_servers()))
            },
            'menu_servers': defined_servers,
            'hosts_data': self.controller.management.get_latest_hosts_stats(),
            'show_contribute': helper.get_setting("show_contribute_link", True),
            'error': error,
            'time': formatted_time
        }
        page_data['lang'] = self.controller.users.get_user_lang_by_id(exec_user_id)
        page_data['super_user'] = exec_user['superuser']

        if page == 'unauthorized':
            template = "panel/denied.html"

        elif page == "error":
            template = "public/error.html"

        elif page == 'credits':
            with open(helper.credits_cache) as republic_credits_will_do:
                credits = json.load(republic_credits_will_do)
                timestamp = credits["lastUpdate"] / 1000.0
                page_data["patrons"] = credits["patrons"]
                page_data["staff"] = credits["staff"]
                page_data["translations"] = credits["translations"]
                page_data["lastUpdate"] = str(datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'))
            template = "panel/credits.html"

        elif page == 'contribute':
            template = "panel/contribute.html"

        elif page == "remove_server":
            server_id = self.get_argument('id', None)

            if not exec_user['superuser']:
                self.redirect("/panel/error?error=Unauthorized access: not superuser")
                return
            elif server_id is None:
                self.redirect("/panel/error?error=Invalid Server ID")
                return

            server_data = self.controller.get_server_data(server_id)
            server_name = server_data['server_name']

            self.controller.management.add_to_audit_log(exec_user_data['user_id'],
                                       "Deleted server {} named {}".format(server_id, server_name),
                                       server_id,
                                       self.get_remote_ip())

            self.controller.remove_server(server_id)
            self.redirect("/panel/dashboard")
            return

        elif page == 'dashboard':
            if exec_user['superuser'] == 1:
                try:
                    page_data['servers'] = self.controller.servers.get_all_servers_stats()
                except IndexError:
                    self.controller.stats.record_stats()
                    page_data['servers'] = self.controller.servers.get_all_servers_stats()

                for data in page_data['servers']:
                    try:
                        data['stats']['waiting_start'] = self.controller.servers.get_waiting_start(int(data['stats']['server_id']['server_id']))
                    except:
                        data['stats']['waiting_start'] = False
            else:
                try:
                    user_auth = self.controller.servers.get_authorized_servers_stats(exec_user_id)
                except IndexError:
                    self.controller.stats.record_stats()
                    user_auth = self.controller.servers.get_authorized_servers_stats(exec_user_id)
                logger.debug("ASFR: {}".format(user_auth))
                page_data['servers'] = user_auth
                page_data['server_stats']['running'] = 0
                page_data['server_stats']['stopped'] = 0
                for data in page_data['servers']:
                    if data['stats']['running']:
                        page_data['server_stats']['running'] += 1
                    else:
                        page_data['server_stats']['stopped'] += 1
                    try:
                        page_data['stats']['waiting_start'] = self.controller.servers.get_waiting_start(int(data['stats']['server_id']['server_id']))
                    except:
                        data['stats']['waiting_start'] = False

            page_data['num_players'] = 0

            IOLoop.current().add_callback(self.fetch_server_data, page_data)

            template = "panel/dashboard.html"

        elif page == 'server_detail':
            server_id = self.get_argument('id', None)
            subpage = bleach.clean(self.get_argument('subpage', ""))

            if server_id is None:
                self.redirect("/panel/error?error=Invalid Server ID")
                return
            else:
                # does this server id exist?
                if not self.controller.servers.server_id_exists(server_id):
                    self.redirect("/panel/error?error=Invalid Server ID")
                    return

                if exec_user['superuser'] != 1:
                    if not self.controller.servers.server_id_authorized(server_id, exec_user_id):
                        if not self.controller.servers.server_id_authorized(int(server_id), exec_user_id):
                            self.redirect("/panel/error?error=Invalid Server ID")
                            return False

            valid_subpages = ['term', 'logs', 'backup', 'config', 'files', 'admin_controls', 'tasks']

            if subpage not in valid_subpages:
                logger.debug('not a valid subpage')
                subpage = 'term'
            logger.debug('Subpage: "{}"'.format(subpage))

            server = self.controller.get_server_obj(server_id)
            # server_data isn't needed since the server_stats also pulls server data
            page_data['server_data'] = self.controller.servers.get_server_data_by_id(server_id)
            page_data['server_stats'] = self.controller.servers.get_server_stats_by_id(server_id)
            try:
                page_data['waiting_start'] = self.controller.servers.get_waiting_start(server_id)
            except:
                page_data['waiting_start'] = False
            page_data['get_players'] = lambda: self.controller.stats.get_server_players(server_id)
            page_data['active_link'] = subpage
            page_data['permissions'] = {
                'Commands': Enum_Permissions_Server.Commands,
                'Terminal': Enum_Permissions_Server.Terminal,
                'Logs': Enum_Permissions_Server.Logs,
                'Schedule': Enum_Permissions_Server.Schedule,
                'Backup': Enum_Permissions_Server.Backup,
                'Files': Enum_Permissions_Server.Files,
                'Config': Enum_Permissions_Server.Config,
                'Players': Enum_Permissions_Server.Players,
            }
            page_data['user_permissions'] = self.controller.server_perms.get_server_permissions_foruser(exec_user_id, server_id)

            if subpage == 'term':
                if not page_data['permissions']['Terminal'] in page_data['user_permissions']:
                    if not exec_user['superuser']:
                        self.redirect("/panel/error?error=Unauthorized access to Terminal")
                        return

            if subpage == 'logs':
                if not page_data['permissions']['Logs'] in page_data['user_permissions']:
                    if not exec_user['superuser']:
                        self.redirect("/panel/error?error=Unauthorized access to Logs")    
                        return     


            if subpage == 'tasks':
                if not page_data['permissions']['Schedule'] in page_data['user_permissions']:
                    if not exec_user['superuser']:
                        self.redirect("/panel/error?error=Unauthorized access To Scheduled Tasks")
                        return
                page_data['schedules'] = management_helper.get_schedules_by_server(server_id)

            if subpage == 'config':
                if not page_data['permissions']['Config'] in page_data['user_permissions']:
                    if not exec_user['superuser']:
                        self.redirect("/panel/error?error=Unauthorized access Server Config")
                        return

            if subpage == 'files':
                if not page_data['permissions']['Files'] in page_data['user_permissions']:
                    if not exec_user['superuser']:
                        self.redirect("/panel/error?error=Unauthorized access Files")
                        return


            if subpage == "backup":
                if not page_data['permissions']['Backup'] in page_data['user_permissions']:
                    if not exec_user['superuser']:
                        self.redirect("/panel/error?error=Unauthorized access to Backups")
                        return
                server_info = self.controller.servers.get_server_data_by_id(server_id)
                page_data['backup_config'] = self.controller.management.get_backup_config(server_id)
                self.controller.refresh_server_settings(server_id)
                try:
                    page_data['backup_list'] = server.list_backups()
                except:
                    page_data['backup_list'] = []
                page_data['backup_path'] = helper.wtol_path(server_info["backup_path"])

            def get_banned_players_html():
                banned_players = self.controller.servers.get_banned_players(server_id)
                if banned_players is None:
                    return """
                    <li class="playerItem banned">
                        <h3>Error while reading banned-players.json</h3>
                    </li>
                    """
                html = ""
                for player in banned_players:
                    html += """
                    <li class="playerItem banned">
                        <h3>{}</h3>
                        <span>Banned by {} for reason: {}</span>
                        <button onclick="send_command_to_server('pardon {}')" type="button" class="btn btn-danger">Unban</button>
                    </li>
                    """.format(player['name'], player['source'], player['reason'], player['name'])

                return html
            if subpage == "admin_controls":
                if not page_data['permissions']['Players'] in page_data['user_permissions']:
                    if not exec_user['superuser']:
                        self.redirect("/panel/error?error=Unauthorized access")
                page_data['banned_players'] = get_banned_players_html()

            # template = "panel/server_details.html"
            template = "panel/server_{subpage}.html".format(subpage=subpage)

        elif page == 'download_backup':
            server_id = self.get_argument('id', None)
            file = self.get_argument('file', "")

            if server_id is None:
                self.redirect("/panel/error?error=Invalid Server ID")
                return
            else:
                # does this server id exist?
                if not self.controller.servers.server_id_exists(server_id):
                    self.redirect("/panel/error?error=Invalid Server ID")
                    return

                if exec_user['superuser'] != 1:
                    #if not self.controller.servers.server_id_authorized(server_id, exec_user_id):
                    if not self.controller.servers.server_id_authorized(int(server_id), exec_user_id):
                        self.redirect("/panel/error?error=Invalid Server ID")
                        return

            server_info = self.controller.servers.get_server_data_by_id(server_id)
            backup_file = os.path.abspath(os.path.join(helper.get_os_understandable_path(server_info["backup_path"]), file))
            if not helper.in_path(helper.get_os_understandable_path(server_info["backup_path"]), backup_file) \
                    or not os.path.isfile(backup_file):
                self.redirect("/panel/error?error=Invalid path detected")
                return

            self.set_header('Content-Type', 'application/octet-stream')
            self.set_header('Content-Disposition', 'attachment; filename=' + file)
            chunk_size = 1024 * 1024 * 4 # 4 MiB

            with open(backup_file, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    try:
                        self.write(chunk) # write the chunk to response
                        self.flush() # send the chunk to client
                    except iostream.StreamClosedError:
                        # this means the client has closed the connection
                        # so break the loop
                        break
                    finally:
                        # deleting the chunk is very important because
                        # if many clients are downloading files at the
                        # same time, the chunks in memory will keep
                        # increasing and will eat up the RAM
                        del chunk
            self.redirect("/panel/server_detail?id={}&subpage=backup".format(server_id))

        elif page == 'backup_now':
            server_id = self.get_argument('id', None)

            if server_id is None:
                self.redirect("/panel/error?error=Invalid Server ID")
                return
            else:
                # does this server id exist?
                if not self.controller.servers.server_id_exists(server_id):
                    self.redirect("/panel/error?error=Invalid Server ID")
                    return

                if exec_user['superuser'] != 1:
                    #if not self.controller.servers.server_id_authorized(server_id, exec_user_id):
                    if not self.controller.servers.server_id_authorized(int(server_id), exec_user_id):
                        self.redirect("/panel/error?error=Invalid Server ID")
                        return

            server = self.controller.get_server_obj(server_id).backup_server()
            self.redirect("/panel/server_detail?id={}&subpage=backup".format(server_id))

        elif page == 'panel_config':
            auth_servers = {}
            auth_role_servers = {}
            users_list = []
            role_users = {}
            roles = self.controller.roles.get_all_roles()
            user_roles = {}
            for user in self.controller.users.get_all_users():
                user_roles_list = self.controller.users.get_user_roles_names(user.user_id)
                user_servers = self.controller.servers.get_authorized_servers(user.user_id)
                servers = []
                for server in user_servers:
                    if server['server_name'] not in servers:
                        servers.append(server['server_name'])
                new_item = {user.user_id: servers}
                auth_servers.update(new_item)
                data = {user.user_id: user_roles_list}
                user_roles.update(data)
            for role in roles:
                role_servers = []
                role = self.controller.roles.get_role_with_servers(role.role_id)
                for serv_id in role['servers']:
                    role_servers.append(self.controller.servers.get_server_data_by_id(serv_id)['server_name'])
                data = {role['role_id']: role_servers}
                auth_role_servers.update(data)


            page_data['auth-servers'] = auth_servers
            page_data['role-servers'] = auth_role_servers
            page_data['user-roles'] = user_roles

            page_data['users'] = self.controller.users.user_query(exec_user['user_id'])
            page_data['roles'] = self.controller.users.user_role_query(exec_user['user_id'])


            for user in page_data['users']:
                if user.user_id != exec_user['user_id']:
                    user.api_token = "********"
            if exec_user['superuser']:
                for user in self.controller.users.get_all_users():
                    if user.superuser == 1:
                        super_auth_servers = []
                        super_auth_servers.append("Super User Access To All Servers")
                        page_data['users'] = self.controller.users.get_all_users()
                        page_data['roles'] = self.controller.roles.get_all_roles()
                        page_data['auth-servers'][user.user_id] = super_auth_servers

            template = "panel/panel_config.html"

        elif page == "add_user":
            page_data['new_user'] = True
            page_data['user'] = {}
            page_data['user']['username'] = ""
            page_data['user']['user_id'] = -1
            page_data['user']['email'] = ""
            page_data['user']['enabled'] = True
            page_data['user']['superuser'] = False
            page_data['user']['api_token'] = "N/A"
            page_data['user']['created'] = "N/A"
            page_data['user']['last_login'] = "N/A"
            page_data['user']['last_ip'] = "N/A"
            page_data['user']['last_update'] = "N/A"
            page_data['user']['roles'] = set()

            if Enum_Permissions_Crafty.User_Config not in exec_user_crafty_permissions:
                self.redirect("/panel/error?error=Unauthorized access: not a user editor")
                return

            page_data['roles_all'] = self.controller.roles.get_all_roles()
            page_data['servers'] = []
            page_data['servers_all'] = self.controller.list_defined_servers()
            page_data['role-servers'] = []
            page_data['permissions_all'] = self.controller.crafty_perms.list_defined_crafty_permissions()
            page_data['permissions_list'] = set()
            page_data['quantity_server'] = self.controller.crafty_perms.list_all_crafty_permissions_quantity_limits()
            page_data['languages'] = []
            page_data['languages'].append(self.controller.users.get_user_lang_by_id(exec_user_id))
            if exec_user['superuser']:
                page_data['super-disabled'] = ''
            else:
                page_data['super-disabled'] = 'disabled'
            for file in os.listdir(os.path.join(helper.root_dir, 'app', 'translations')):
                if file.endswith('.json'):
                    if file != str(page_data['languages'][0] + '.json'):
                        page_data['languages'].append(file.split('.')[0])

            template = "panel/panel_edit_user.html"

        elif page == "edit_user":
            user_id = self.get_argument('id', None)
            role_servers = self.controller.servers.get_authorized_servers(user_id)
            page_role_servers = []
            servers = set()
            for server in role_servers:
                page_role_servers.append(server['server_id'])
            page_data['new_user'] = False
            page_data['user'] = self.controller.users.get_user_by_id(user_id)
            page_data['servers'] = servers
            page_data['role-servers'] = page_role_servers
            page_data['roles_all'] = self.controller.roles.get_all_roles()
            page_data['servers_all'] = self.controller.list_defined_servers()
            page_data['permissions_all'] = self.controller.crafty_perms.list_defined_crafty_permissions()
            page_data['permissions_list'] = self.controller.crafty_perms.get_crafty_permissions_list(user_id)
            page_data['quantity_server'] = self.controller.crafty_perms.list_crafty_permissions_quantity_limits(user_id)
            page_data['languages'] = []
            page_data['languages'].append(self.controller.users.get_user_lang_by_id(user_id))
            #checks if super user. If not we disable the button.
            if exec_user['superuser'] and str(exec_user['user_id']) != str(user_id):
                page_data['super-disabled'] = ''
            else:
                page_data['super-disabled'] = 'disabled'
            
            for file in sorted(os.listdir(os.path.join(helper.root_dir, 'app', 'translations'))):
                if file.endswith('.json'):
                    if file != str(page_data['languages'][0] + '.json'):
                        page_data['languages'].append(file.split('.')[0])

            if user_id is None:
                self.redirect("/panel/error?error=Invalid User ID")
                return
            elif Enum_Permissions_Crafty.User_Config not in exec_user_crafty_permissions:
                if str(user_id) != str(exec_user_id):
                    self.redirect("/panel/error?error=Unauthorized access: not a user editor")
                    return

                page_data['servers'] = []
                page_data['role-servers'] = []
                page_data['roles_all'] = []
                page_data['servers_all'] = []

            if exec_user['user_id'] != page_data['user']['user_id']:
                page_data['user']['api_token'] = "********"

            if exec_user['email'] == 'default@example.com':
                page_data['user']['email'] = ""
            template = "panel/panel_edit_user.html"

        elif page == "remove_user":
            user_id = bleach.clean(self.get_argument('id', None))
            
            if not exec_user['superuser'] and Enum_Permissions_Crafty.User_Config not in exec_user_crafty_permissions:
                self.redirect("/panel/error?error=Unauthorized access: not superuser")
                return

            elif str(exec_user_id) == str(user_id):
                self.redirect("/panel/error?error=Unauthorized access: you cannot delete yourself")
                return
            elif user_id is None:
                self.redirect("/panel/error?error=Invalid User ID")
                return
            else:
                # does this user id exist?
                target_user = self.controller.users.get_user_by_id(user_id)
                if not target_user:
                    self.redirect("/panel/error?error=Invalid User ID")
                    return
                elif target_user['superuser']:
                    self.redirect("/panel/error?error=Cannot remove a superuser")
                    return

            self.controller.users.remove_user(user_id)

            self.controller.management.add_to_audit_log(exec_user['user_id'],
                                       "Removed user {} (UID:{})".format(target_user['username'], user_id),
                                       server_id=0,
                                       source_ip=self.get_remote_ip())
            self.redirect("/panel/panel_config")

        elif page == "add_role":
            user_roles = {}
            for user in self.controller.users.get_all_users():
                user_roles_list = self.controller.users.get_user_roles_names(user.user_id)
                user_servers = self.controller.servers.get_authorized_servers(user.user_id)
                data = {user.user_id: user_roles_list}
                user_roles.update(data)
            page_data['new_role'] = True
            page_data['role'] = {}
            page_data['role']['role_name'] = ""
            page_data['role']['role_id'] = -1
            page_data['role']['created'] = "N/A"
            page_data['role']['last_update'] = "N/A"
            page_data['role']['servers'] = set()
            page_data['user-roles'] = user_roles
            page_data['users'] = self.controller.users.get_all_users()

            if Enum_Permissions_Crafty.Roles_Config not in exec_user_crafty_permissions:
                self.redirect("/panel/error?error=Unauthorized access: not a role editor")
                return

            page_data['servers_all'] = self.controller.list_defined_servers()
            page_data['permissions_all'] = self.controller.server_perms.list_defined_permissions()
            page_data['permissions_list'] = set()
            template = "panel/panel_edit_role.html"

        elif page == "edit_role":
            auth_servers = {}

            user_roles = {}
            for user in self.controller.users.get_all_users():
                user_roles_list = self.controller.users.get_user_roles_names(user.user_id)
                user_servers = self.controller.servers.get_authorized_servers(user.user_id)
                data = {user.user_id: user_roles_list}
                user_roles.update(data)
            page_data['new_role'] = False
            role_id = self.get_argument('id', None)
            page_data['role'] = self.controller.roles.get_role_with_servers(role_id)
            page_data['servers_all'] = self.controller.list_defined_servers()
            page_data['permissions_all'] = self.controller.server_perms.list_defined_permissions()
            page_data['permissions_list'] = self.controller.server_perms.get_role_permissions(role_id)
            page_data['user-roles'] = user_roles
            page_data['users'] = self.controller.users.get_all_users()

            if Enum_Permissions_Crafty.Roles_Config not in exec_user_crafty_permissions:
                self.redirect("/panel/error?error=Unauthorized access: not a role editor")
                return
            elif role_id is None:
                self.redirect("/panel/error?error=Invalid Role ID")
                return

            template = "panel/panel_edit_role.html"

        elif page == "remove_role":
            role_id = bleach.clean(self.get_argument('id', None))

            if not exec_user['superuser']:
                self.redirect("/panel/error?error=Unauthorized access: not superuser")
                return
            elif role_id is None:
                self.redirect("/panel/error?error=Invalid Role ID")
                return
            else:
                # does this user id exist?
                target_role = self.controller.roles.get_role(role_id)
                if not target_role:
                    self.redirect("/panel/error?error=Invalid Role ID")
                    return

            self.controller.roles.remove_role(role_id)

            self.controller.management.add_to_audit_log(exec_user['user_id'],
                                       "Removed role {} (RID:{})".format(target_role['role_name'], role_id),
                                       server_id=0,
                                       source_ip=self.get_remote_ip())
            self.redirect("/panel/panel_config")

        elif page == "activity_logs":
            page_data['audit_logs'] = self.controller.management.get_actity_log()

            template = "panel/activity_logs.html"

        elif page == 'download_file':
            server_id = self.get_argument('id', None)
            file = helper.get_os_understandable_path(self.get_argument('path', ""))
            name = self.get_argument('name', "")

            if server_id is None:
                self.redirect("/panel/error?error=Invalid Server ID")
                return
            else:
                # does this server id exist?
                if not self.controller.servers.server_id_exists(server_id):
                    self.redirect("/panel/error?error=Invalid Server ID")
                    return

                if exec_user['superuser'] != 1:
                    if not self.controller.servers.server_id_authorized(int(server_id), exec_user_id):
                        self.redirect("/panel/error?error=Invalid Server ID")
                        return

            server_info = self.controller.servers.get_server_data_by_id(server_id)

            if not helper.in_path(helper.get_os_understandable_path(server_info["path"]), file) \
                    or not os.path.isfile(file):
                self.redirect("/panel/error?error=Invalid path detected")
                return

            self.set_header('Content-Type', 'application/octet-stream')
            self.set_header('Content-Disposition', 'attachment; filename=' + name)
            chunk_size = 1024 * 1024 * 4 # 4 MiB

            with open(file, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    try:
                        self.write(chunk) # write the chunk to response
                        self.flush() # send the chunk to client
                    except iostream.StreamClosedError:
                        # this means the client has closed the connection
                        # so break the loop
                        break
                    finally:
                        # deleting the chunk is very important because
                        # if many clients are downloading files at the
                        # same time, the chunks in memory will keep
                        # increasing and will eat up the RAM
                        del chunk
            self.redirect("/panel/server_detail?id={}&subpage=files".format(server_id))


        self.render(
            template,
            data=page_data,
            time=time,
            utc_offset=(time.timezone * -1 / 60 / 60),
            translate=self.translator.translate,
        )

    @tornado.web.authenticated
    def post(self, page):
        exec_user_data = json.loads(self.get_secure_cookie("user_data"))
        exec_user_id = exec_user_data['user_id']
        exec_user = self.controller.users.get_user_by_id(exec_user_id)
        server_id = self.get_argument('id', None)
        permissions = {
                'Commands': Enum_Permissions_Server.Commands,
                'Terminal': Enum_Permissions_Server.Terminal,
                'Logs': Enum_Permissions_Server.Logs,
                'Schedule': Enum_Permissions_Server.Schedule,
                'Backup': Enum_Permissions_Server.Backup,
                'Files': Enum_Permissions_Server.Files,
                'Config': Enum_Permissions_Server.Config,
                'Players': Enum_Permissions_Server.Players,
            }
        user_perms = self.controller.server_perms.get_server_permissions_foruser(exec_user_id, server_id)
        exec_user_role = set()
        if exec_user['superuser'] == 1:
            defined_servers = self.controller.list_defined_servers()
            exec_user_role.add("Super User")
            exec_user_crafty_permissions = self.controller.crafty_perms.list_defined_crafty_permissions()
        else:
            exec_user_crafty_permissions = self.controller.crafty_perms.get_crafty_permissions_list(exec_user_id)
            defined_servers = self.controller.servers.get_authorized_servers(exec_user_id)
            for r in exec_user['roles']:
                role = self.controller.roles.get_role(r)
                exec_user_role.add(role['role_name'])

        if page == 'server_detail':
            if not permissions['Config'] in user_perms:
                if not exec_user['superuser']:
                    self.redirect("/panel/error?error=Unauthorized access to Config")    
                    return         
            server_id = self.get_argument('id', None)
            server_name = self.get_argument('server_name', None)
            server_obj = self.controller.servers.get_server_obj(server_id)
            if exec_user['superuser']:
                server_path = self.get_argument('server_path', None)
                log_path = self.get_argument('log_path', None)
                executable = self.get_argument('executable', None)
                execution_command = self.get_argument('execution_command', None)
                server_ip = self.get_argument('server_ip', None)
                server_port = self.get_argument('server_port', None)
                executable_update_url = self.get_argument('executable_update_url', None)
            else:
                execution_command = server_obj.execution_command
                executable = server_obj.executable
            stop_command = self.get_argument('stop_command', None)
            auto_start_delay = self.get_argument('auto_start_delay', '10')
            auto_start = int(float(self.get_argument('auto_start', '0')))
            crash_detection = int(float(self.get_argument('crash_detection', '0')))
            logs_delete_after = int(float(self.get_argument('logs_delete_after', '0')))
            subpage = self.get_argument('subpage', None)

            if not exec_user['superuser']:
                if not self.controller.servers.server_id_authorized(server_id, exec_user_id):
                    self.redirect("/panel/error?error=Unauthorized access: invalid server id")
                    return
            elif server_id is None:
                self.redirect("/panel/error?error=Invalid Server ID")
                return
            else:
                # does this server id exist?
                if not self.controller.servers.server_id_exists(server_id):
                    self.redirect("/panel/error?error=Invalid Server ID")
                    return

            server_obj = self.controller.servers.get_server_obj(server_id)
            server_settings = self.controller.get_server_data(server_id)
            stale_executable = server_obj.executable
            #Compares old jar name to page data being passed. If they are different we replace the executable name in the
            if str(stale_executable) != str(executable):
                execution_command = execution_command.replace(str(stale_executable), str(executable))

            server_obj.server_name = server_name
            if exec_user['superuser']:
                if helper.validate_traversal(helper.get_servers_root_dir(), server_path):
                    server_obj.path = server_path
                    server_obj.log_path = log_path
                if helper.validate_traversal(helper.get_servers_root_dir(), executable):
                    server_obj.executable = executable
                server_obj.execution_command = execution_command
                server_obj.server_ip = server_ip
                server_obj.server_port = server_port
                server_obj.executable_update_url = executable_update_url
            else:
                server_obj.path = server_obj.path
                server_obj.log_path = server_obj.log_path
                server_obj.executable = server_obj.executable
                print(server_obj.execution_command)
                server_obj.execution_command = server_obj.execution_command
                server_obj.server_ip = server_obj.server_ip
                server_obj.server_port = server_obj.server_port
                server_obj.executable_update_url = server_obj.executable_update_url
            server_obj.stop_command = stop_command
            server_obj.auto_start_delay = auto_start_delay
            server_obj.auto_start = auto_start
            server_obj.crash_detection = crash_detection
            server_obj.logs_delete_after = logs_delete_after
            self.controller.servers.update_server(server_obj)

            self.controller.refresh_server_settings(server_id)

            self.controller.management.add_to_audit_log(exec_user['user_id'],
                                       "Edited server {} named {}".format(server_id, server_name),
                                       server_id,
                                       self.get_remote_ip())

            self.redirect("/panel/server_detail?id={}&subpage=config".format(server_id))

        if page == "server_backup":
            logger.debug(self.request.arguments)
            server_id = self.get_argument('id', None)
            server_obj = self.controller.servers.get_server_obj(server_id)
            if exec_user['superuser']:
                backup_path = bleach.clean(self.get_argument('backup_path', None))
            else:
                backup_path = server_obj.backup_path
            max_backups = bleach.clean(self.get_argument('max_backups', None))
            try:
                enabled = int(float(bleach.clean(self.get_argument('auto_enabled'), '0')))
            except Exception as e:
                enabled = '0'

            if not permissions['Backup'] in user_perms:
                if not exec_user['superuser']:
                    self.redirect("/panel/error?error=Unauthorized access: User not authorized")
                return
            elif server_id is None:
                self.redirect("/panel/error?error=Invalid Server ID")
                return
            else:
                # does this server id exist?
                if not self.controller.servers.server_id_exists(server_id):
                    self.redirect("/panel/error?error=Invalid Server ID")
                    return

                if enabled == '0':
                    #TODO Use Controller method
                    server_obj = self.controller.servers.get_server_obj(server_id)
                    server_obj.backup_path = backup_path
                    self.controller.servers.update_server(server_obj)
                    self.controller.management.set_backup_config(server_id, max_backups=max_backups, auto_enabled=False)
                else:
                    #TODO Use Controller method
                    server_obj = self.controller.servers.get_server_obj(server_id)
                    server_obj.backup_path = backup_path
                    self.controller.servers.update_server(server_obj)
                    self.controller.management.set_backup_config(server_id, max_backups=max_backups, auto_enabled=True)

            self.controller.management.add_to_audit_log(exec_user['user_id'],
                                       "Edited server {}: updated backups".format(server_id),
                                       server_id,
                                       self.get_remote_ip())
            self.tasks_manager.reload_schedule_from_db()
            self.redirect("/panel/server_detail?id={}&subpage=backup".format(server_id))

        elif page == "edit_user":
            if bleach.clean(self.get_argument('username', None)) == 'system':
                self.redirect("/panel/error?error=Unauthorized access: system user is not editable")
            user_id = bleach.clean(self.get_argument('id', None))
            username = bleach.clean(self.get_argument('username', None))
            password0 = bleach.clean(self.get_argument('password0', None))
            password1 = bleach.clean(self.get_argument('password1', None))
            email = bleach.clean(self.get_argument('email', "default@example.com"))
            enabled = int(float(self.get_argument('enabled', '0')))
            regen_api = int(float(self.get_argument('regen_api', '0')))
            lang = bleach.clean(self.get_argument('language'), 'en_EN')
            if exec_user['superuser']:
                #Checks if user is trying to change super user status of self. We don't want that. Automatically make them stay super user since we know they are.
                if str(exec_user['user_id']) != str(user_id):
                    superuser = bleach.clean(self.get_argument('superuser', '0'))
                else:
                    superuser = '1'
            else:
                superuser = '0'
            if superuser == '1':
                superuser = True
            else:
                superuser = False

            if Enum_Permissions_Crafty.User_Config not in exec_user_crafty_permissions:
                if str(user_id) != str(exec_user_id):
                    self.redirect("/panel/error?error=Unauthorized access: not a user editor")
                    return

                user_data = {
                    "username": username,
                    "password": password0,
                    "lang": lang,
                }
                self.controller.users.update_user(user_id, user_data=user_data)

                self.controller.management.add_to_audit_log(exec_user['user_id'],
                                           "Edited user {} (UID:{}) password".format(username,
                                                                                                         user_id),
                                           server_id=0,
                                           source_ip=self.get_remote_ip())
                self.redirect("/panel/panel_config")
                return
            elif username is None or username == "":
                self.redirect("/panel/error?error=Invalid username")
                return
            elif user_id is None:
                self.redirect("/panel/error?error=Invalid User ID")
                return
            else:
                # does this user id exist?
                if not self.controller.users.user_id_exists(user_id):
                    self.redirect("/panel/error?error=Invalid User ID")
                    return

            if password0 != password1:
                self.redirect("/panel/error?error=Passwords must match")
                return

            roles = set()
            for role in self.controller.roles.get_all_roles():
                argument = int(float(
                    bleach.clean(
                        self.get_argument('role_{}_membership'.format(role.role_id), '0')
                    )
                ))
                if argument:
                    roles.add(role.role_id)

            permissions_mask = "000"
            server_quantity = {}
            for permission in self.controller.crafty_perms.list_defined_crafty_permissions():
                argument = int(float(
                    bleach.clean(
                        self.get_argument('permission_{}'.format(permission.name), '0')
                    )
                ))
                if argument:
                    permissions_mask = self.controller.crafty_perms.set_permission(permissions_mask, permission, argument)

                q_argument = int(float(
                    bleach.clean(
                        self.get_argument('quantity_{}'.format(permission.name), '0')
                    )
                ))
                if q_argument:
                    server_quantity[permission.name] = q_argument
                else:
                    server_quantity[permission.name] = 0

            # if email is None or "":
            #     email = "default@example.com"

            user_data = {
                "username": username,
                "password": password0,
                "email": email,
                "enabled": enabled,
                "regen_api": regen_api,
                "roles": roles,
                "lang": lang,
                "superuser": superuser,
            }
            user_crafty_data = {
                "permissions_mask": permissions_mask,
                "server_quantity": server_quantity
            }
            self.controller.users.update_user(user_id, user_data=user_data, user_crafty_data=user_crafty_data)

            self.controller.management.add_to_audit_log(exec_user['user_id'],
                                       "Edited user {} (UID:{}) with roles {} and permissions {}".format(username, user_id, roles, permissions_mask),
                                       server_id=0,
                                       source_ip=self.get_remote_ip())
            self.redirect("/panel/panel_config")


        elif page == "add_user":
            if bleach.clean(self.get_argument('username', None)).lower() == 'system':
                self.redirect("/panel/error?error=Unauthorized access: username system is reserved for the Crafty system. Please choose a different username.")
                return
            username = bleach.clean(self.get_argument('username', None))
            password0 = bleach.clean(self.get_argument('password0', None))
            password1 = bleach.clean(self.get_argument('password1', None))
            email  = bleach.clean(self.get_argument('email', "default@example.com"))
            enabled = int(float(self.get_argument('enabled', '0'))),
            lang = bleach.clean(self.get_argument('lang', 'en_EN'))
            if exec_user['superuser']:
                superuser = bleach.clean(self.get_argument('superuser', '0'))
            else:
                superuser = '0'
            if superuser == '1':
                superuser = True
            else:
                superuser = False            

            if Enum_Permissions_Crafty.User_Config not in exec_user_crafty_permissions:
                self.redirect("/panel/error?error=Unauthorized access: not a user editor")
                return
            elif username is None or username == "":
                self.redirect("/panel/error?error=Invalid username")
                return
            else:
                # does this user id exist?
                if self.controller.users.get_id_by_name(username) is not None:
                    self.redirect("/panel/error?error=User exists")
                    return

            if password0 != password1:
                self.redirect("/panel/error?error=Passwords must match")
                return

            roles = set()
            for role in self.controller.roles.get_all_roles():
                argument = int(float(
                    bleach.clean(
                        self.get_argument('role_{}_membership'.format(role.role_id), '0')
                    )
                ))
                if argument:
                    roles.add(role.role_id)

            permissions_mask = "000"
            server_quantity = {}
            for permission in self.controller.crafty_perms.list_defined_crafty_permissions():
                argument = int(float(
                    bleach.clean(
                        self.get_argument('permission_{}'.format(permission.name), '0')
                    )
                ))
                if argument:
                    permissions_mask = self.controller.crafty_perms.set_permission(permissions_mask, permission, argument)

                q_argument = int(float(
                    bleach.clean(
                        self.get_argument('quantity_{}'.format(permission.name), '0')
                    )
                ))
                if q_argument:
                    server_quantity[permission.name] = q_argument
                else:
                    server_quantity[permission.name] = 0

            user_id = self.controller.users.add_user(username, password=password0, email=email, enabled=enabled, superuser=superuser)
            user_data = {
                "roles": roles,
                'lang': lang
            }
            user_crafty_data = {
                "permissions_mask": permissions_mask,
                "server_quantity": server_quantity
            }
            self.controller.users.update_user(user_id, user_data=user_data, user_crafty_data=user_crafty_data)

            self.controller.management.add_to_audit_log(exec_user['user_id'],
                                       "Added user {} (UID:{})".format(username, user_id),
                                       server_id=0,
                                       source_ip=self.get_remote_ip())
            self.controller.management.add_to_audit_log(exec_user['user_id'],
                                       "Edited user {} (UID:{}) with roles {}".format(username, user_id, roles),
                                       server_id=0,
                                       source_ip=self.get_remote_ip())
            self.redirect("/panel/panel_config")

        elif page == "edit_role":
            role_id = bleach.clean(self.get_argument('id', None))
            role_name = bleach.clean(self.get_argument('role_name', None))

            if Enum_Permissions_Crafty.Roles_Config not in exec_user_crafty_permissions:
                self.redirect("/panel/error?error=Unauthorized access: not a role editor")
                return
            elif role_name is None or role_name == "":
                self.redirect("/panel/error?error=Invalid username")
                return
            elif role_id is None:
                self.redirect("/panel/error?error=Invalid Role ID")
                return
            else:
                # does this user id exist?
                if not self.controller.roles.role_id_exists(role_id):
                    self.redirect("/panel/error?error=Invalid Role ID")
                    return

            servers = set()
            for server in self.controller.list_defined_servers():
                argument = int(float(
                    bleach.clean(
                        self.get_argument('server_{}_access'.format(server['server_id']), '0')
                    )
                ))
                if argument:
                    servers.add(server['server_id'])

            permissions_mask = "00000000"
            for permission in self.controller.server_perms.list_defined_permissions():
                argument = int(float(
                    bleach.clean(
                        self.get_argument('permission_{}'.format(permission.name), '0')
                    )
                ))
                if argument:
                    permissions_mask = self.controller.server_perms.set_permission(permissions_mask, permission, argument)

            role_data = {
                "role_name": role_name,
                "servers": servers
            }
            self.controller.roles.update_role(role_id, role_data=role_data, permissions_mask=permissions_mask)

            self.controller.management.add_to_audit_log(exec_user['user_id'],
                                       "Edited role {} (RID:{}) with servers {}".format(role_name, role_id, servers),
                                       server_id=0,
                                       source_ip=self.get_remote_ip())
            self.redirect("/panel/panel_config")


        elif page == "add_role":
            role_name = bleach.clean(self.get_argument('role_name', None))

            if Enum_Permissions_Crafty.Roles_Config not in exec_user_crafty_permissions:
                self.redirect("/panel/error?error=Unauthorized access: not a role editor")
                return
            elif role_name is None or role_name == "":
                self.redirect("/panel/error?error=Invalid role name")
                return
            else:
                # does this user id exist?
                if self.controller.roles.get_roleid_by_name(role_name) is not None:
                    self.redirect("/panel/error?error=Role exists")
                    return

            servers = set()
            for server in self.controller.list_defined_servers():
                argument = int(float(
                    bleach.clean(
                        self.get_argument('server_{}_access'.format(server['server_id']), '0')
                    )
                ))
                if argument:
                    servers.add(server['server_id'])

            permissions_mask = "00000000"
            for permission in self.controller.server_perms.list_defined_permissions():
                argument = int(float(
                    bleach.clean(
                        self.get_argument('permission_{}'.format(permission.name), '0')
                    )
                ))
                if argument:
                    permissions_mask = self.controller.server_perms.set_permission(permissions_mask, permission, argument)

            role_id = self.controller.roles.add_role(role_name)
            self.controller.roles.update_role(role_id, {"servers": servers}, permissions_mask)

            self.controller.management.add_to_audit_log(exec_user['user_id'],
                                       "Added role {} (RID:{})".format(role_name, role_id),
                                       server_id=0,
                                       source_ip=self.get_remote_ip())
            self.controller.management.add_to_audit_log(exec_user['user_id'],
                                       "Edited role {} (RID:{}) with servers {}".format(role_name, role_id, servers),
                                       server_id=0,
                                       source_ip=self.get_remote_ip())
            self.redirect("/panel/panel_config")

        else:
            self.set_status(404)
            page_data = []
            page_data['lang'] = tornado.locale.get("en_EN")
            self.render(
                "public/404.html",
                translate=self.translator.translate,
                data=page_data
            )
