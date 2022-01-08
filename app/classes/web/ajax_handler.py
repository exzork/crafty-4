import json
import logging
import tempfile
import threading
from typing import Container
import zipfile

import tornado.web
import tornado.escape
import bleach
import os
import shutil
import html
import re
from app.classes.models.users import helper_users

from app.classes.shared.console import console
from app.classes.shared.main_models import Users, installer
from app.classes.web.base_handler import BaseHandler
from app.classes.shared.helpers import helper
from app.classes.shared.server import ServerOutBuf
from app.classes.models.server_permissions import Enum_Permissions_Server

logger = logging.getLogger(__name__)


class AjaxHandler(BaseHandler):

    def render_page(self, template, page_data):
        self.render(
            template,
            data=page_data,
            translate=self.translator.translate,
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
                return

            server_id = bleach.clean(server_id)

            server_data = self.controller.servers.get_server_data_by_id(server_id)
            if not server_data:
                logger.warning("Server Data not found in server_log ajax call")
                self.redirect("/panel/error?error=Server ID Not Found")
                return

            if not server_data['log_path']:
                logger.warning("Log path not found in server_log ajax call ({})".format(server_id))

            if full_log:
                log_lines = helper.get_setting('max_log_lines')
                data = helper.tail_file(helper.get_os_understandable_path(server_data['log_path']), log_lines)
            else:
                data = ServerOutBuf.lines.get(server_id, [])


            for d in data:
                try:
                    d = re.sub('(\033\\[(0;)?[0-9]*[A-z]?(;[0-9])?m?)|(> )', '', d)
                    d = re.sub('[A-z]{2}\b\b', '', d)
                    line = helper.log_colors(html.escape(d))
                    self.write('{}<br />'.format(line))
                    # self.write(d.encode("utf-8"))

                except Exception as e:
                    logger.warning("Skipping Log Line due to error: {}".format(e))
                    pass

        elif page == "announcements":
            data = helper.get_announcements()
            page_data['notify_data'] = data
            self.render_page('ajax/notify.html', page_data)

        elif page == "get_file":
            file_path = helper.get_os_understandable_path(self.get_argument('file_path', None))
            server_id = self.get_argument('id', None)

            if not self.check_server_id(server_id, 'get_file'): return
            else: server_id = bleach.clean(server_id)

            if not helper.in_path(helper.get_os_understandable_path(self.controller.servers.get_server_data_by_id(server_id)['path']), file_path)\
                or not helper.check_file_exists(os.path.abspath(file_path)):
                logger.warning("Invalid path in get_file ajax call ({})".format(file_path))
                console.warning("Invalid path in get_file ajax call ({})".format(file_path))
                return


            error = None

            try:
                with open(file_path) as file:
                    file_contents = file.read()
            except UnicodeDecodeError:
                file_contents = ''
                error = 'UnicodeDecodeError'

            self.write({
                'content': file_contents,
                'error': error
            })
            self.finish()

        elif page == "get_tree":
            server_id = self.get_argument('id', None)
            path = self.get_argument('path', None)

            if not self.check_server_id(server_id, 'get_tree'): return
            else: server_id = bleach.clean(server_id)

            if helper.validate_traversal(self.controller.servers.get_server_data_by_id(server_id)['path'], path):
                self.write(helper.get_os_understandable_path(path) + '\n' +
                        helper.generate_tree(path))
            self.finish()
        
        elif page == "get_dir":
            server_id = self.get_argument('id', None)
            path = self.get_argument('path', None)

            if not self.check_server_id(server_id, 'get_tree'): return
            else: server_id = bleach.clean(server_id)

            if helper.validate_traversal(self.controller.servers.get_server_data_by_id(server_id)['path'], path):
                self.write(helper.get_os_understandable_path(path) + '\n' +
                        helper.generate_dir(path))
            self.finish()

    @tornado.web.authenticated
    def post(self, page):
        user_data = json.loads(self.get_secure_cookie("user_data"))
        server_id = self.get_argument('id', None)
        exec_user_id = user_data['user_id']
        exec_user = helper_users.get_user(exec_user_id)
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
        error = bleach.clean(self.get_argument('error', "WTF Error!"))

        page_data = {
            'user_data': user_data,
            'error': error
        }

        if page == "send_command":
            command = self.get_body_argument('command', default=None, strip=True)
            server_id = self.get_argument('id')

            if server_id is None:
                logger.warning("Server ID not found in send_command ajax call")
                console.warning("Server ID not found in send_command ajax call")

            srv_obj = self.controller.get_server_obj(server_id)

            if command:
                if srv_obj.check_running():
                    srv_obj.send_command(command)

            self.controller.management.add_to_audit_log(user_data['user_id'], "Sent command to {} terminal: {}".format(self.controller.servers.get_server_friendly_name(server_id), command), server_id, self.get_remote_ip())

        elif page == "create_file":
            if not permissions['Files'] in user_perms:
                if not exec_user['superuser']:
                    self.redirect("/panel/error?error=Unauthorized access to Files")    
                    return             
            file_parent = helper.get_os_understandable_path(self.get_body_argument('file_parent', default=None, strip=True))
            file_name = self.get_body_argument('file_name', default=None, strip=True)
            file_path = os.path.join(file_parent, file_name)
            server_id = self.get_argument('id', None)

            if not self.check_server_id(server_id, 'create_file'): return
            else: server_id = bleach.clean(server_id)

            if not helper.in_path(helper.get_os_understandable_path(self.controller.servers.get_server_data_by_id(server_id)['path']), file_path) \
                or helper.check_file_exists(os.path.abspath(file_path)):
                logger.warning("Invalid path in create_file ajax call ({})".format(file_path))
                console.warning("Invalid path in create_file ajax call ({})".format(file_path))
                return

            # Create the file by opening it
            with open(file_path, 'w') as file_object:
                file_object.close()

        elif page == "create_dir":
            if not permissions['Files'] in user_perms:
                if not exec_user['superuser']:
                    self.redirect("/panel/error?error=Unauthorized access to Files")    
                    return 
            dir_parent = helper.get_os_understandable_path(self.get_body_argument('dir_parent', default=None, strip=True))
            dir_name = self.get_body_argument('dir_name', default=None, strip=True)
            dir_path = os.path.join(dir_parent, dir_name)
            server_id = self.get_argument('id', None)

            if not self.check_server_id(server_id, 'create_dir'): return
            else: server_id = bleach.clean(server_id)

            if not helper.in_path(helper.get_os_understandable_path(self.controller.servers.get_server_data_by_id(server_id)['path']), dir_path) \
                or helper.check_path_exists(os.path.abspath(dir_path)):
                logger.warning("Invalid path in create_dir ajax call ({})".format(dir_path))
                console.warning("Invalid path in create_dir ajax call ({})".format(dir_path))
                return
            # Create the directory
            os.mkdir(dir_path)

        elif page == "unzip_file":
            if not permissions['Files'] in user_perms:
                if not exec_user['superuser']:
                    self.redirect("/panel/error?error=Unauthorized access to Files")    
                    return 
            server_id = self.get_argument('id', None)
            path = helper.get_os_understandable_path(self.get_argument('path', None))
            helper.unzipFile(path)
            self.redirect("/panel/server_detail?id={}&subpage=files".format(server_id))
            return

        elif page == "kill":
            if not permissions['Commands'] in user_perms:
                if not exec_user['superuser']:
                    self.redirect("/panel/error?error=Unauthorized access to Commands")    
                    return 
            server_id = self.get_argument('id', None)
            svr = self.controller.get_server_obj(server_id)
            try:
                svr.kill()
            except Exception as e:
                logger.error("Could not find PID for requested termsig. Full error: {}".format(e))
            return
        elif page == "eula":
            server_id = self.get_argument('id', None)
            svr = self.controller.get_server_obj(server_id)
            svr.agree_eula(user_data['user_id'])

        elif page == "restore_backup":
            if not permissions['Backup'] in user_perms:
                if not exec_user['superuser']:
                    self.redirect("/panel/error?error=Unauthorized access to Backups")    
                    return 
            server_id = bleach.clean(self.get_argument('id', None))
            zip_name = bleach.clean(self.get_argument('zip_file', None))
            svr_obj = self.controller.servers.get_server_obj(server_id)
            server_data = self.controller.servers.get_server_data_by_id(server_id)
            backup_path = svr_obj.backup_path
            if helper.validate_traversal(backup_path, zip_name):
                new_server = self.controller.import_zip_server(svr_obj.server_name, os.path.join(backup_path, zip_name), server_data['executable'], '1', '2', server_data['server_port'])
                new_server_id = new_server
                new_server = self.controller.get_server_data(new_server)
                self.controller.rename_backup_dir(server_id, new_server_id, new_server['server_uuid'])
                self.controller.remove_server(server_id, True)
                self.redirect('/panel/dashboard')
                

    @tornado.web.authenticated
    def delete(self, page):
        user_data = json.loads(self.get_secure_cookie("user_data"))
        server_id = self.get_argument('id', None)
        exec_user_id = user_data['user_id']
        exec_user = helper_users.get_user(exec_user_id)
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
        if page == "del_file":
            if not permissions['Files'] in user_perms:
                if not exec_user['superuser']:
                    self.redirect("/panel/error?error=Unauthorized access to Files")    
                    return            
            file_path = helper.get_os_understandable_path(self.get_body_argument('file_path', default=None, strip=True))
            server_id = self.get_argument('id', None)

            console.warning("delete {} for server {}".format(file_path, server_id))

            if not self.check_server_id(server_id, 'del_file'):
                return
            else: server_id = bleach.clean(server_id)

            server_info = self.controller.servers.get_server_data_by_id(server_id)
            if not (helper.in_path(helper.get_os_understandable_path(server_info['path']), file_path) \
                or helper.in_path(helper.get_os_understandable_path(server_info['backup_path']), file_path)) \
                or not helper.check_file_exists(os.path.abspath(file_path)):
                logger.warning("Invalid path in del_file ajax call ({})".format(file_path))
                console.warning("Invalid path in del_file ajax call ({})".format(file_path))
                return

            # Delete the file
            os.remove(file_path)

        if page == "del_backup":
            if not permissions['Backup'] in user_perms:
                if not exec_user['superuser']:
                    self.redirect("/panel/error?error=Unauthorized access to Backups")    
                    return            
            file_path = helper.get_os_understandable_path(self.get_body_argument('file_path', default=None, strip=True))
            server_id = self.get_argument('id', None)

            console.warning("delete {} for server {}".format(file_path, server_id))

            if not self.check_server_id(server_id, 'del_file'):
                return
            else: server_id = bleach.clean(server_id)

            server_info = self.controller.servers.get_server_data_by_id(server_id)
            if not (helper.in_path(helper.get_os_understandable_path(server_info['path']), file_path) \
                or helper.in_path(helper.get_os_understandable_path(server_info['backup_path']), file_path)) \
                or not helper.check_file_exists(os.path.abspath(file_path)):
                logger.warning("Invalid path in del_file ajax call ({})".format(file_path))
                console.warning("Invalid path in del_file ajax call ({})".format(file_path))
                return

            # Delete the file
            if helper.validate_traversal(helper.get_os_understandable_path(server_info['path']), file_path):
                os.remove(file_path)

        elif page == "del_dir":
            if not permissions['Files'] in user_perms:
                if not exec_user['superuser']:
                    self.redirect("/panel/error?error=Unauthorized access to Files")    
                    return              
            dir_path = helper.get_os_understandable_path(self.get_body_argument('dir_path', default=None, strip=True))
            server_id = self.get_argument('id', None)

            console.warning("delete {} for server {}".format(dir_path, server_id))

            if not self.check_server_id(server_id, 'del_dir'): return
            else: server_id = bleach.clean(server_id)

            server_info = self.controller.servers.get_server_data_by_id(server_id)
            if not helper.in_path(helper.get_os_understandable_path(server_info['path']), dir_path) \
                or not helper.check_path_exists(os.path.abspath(dir_path)):
                logger.warning("Invalid path in del_file ajax call ({})".format(dir_path))
                console.warning("Invalid path in del_file ajax call ({})".format(dir_path))
                return

            # Delete the directory
            # os.rmdir(dir_path)     # Would only remove empty directories
            if helper.validate_traversal(helper.get_os_understandable_path(server_info['path']), dir_path):
                shutil.rmtree(dir_path)  # Removes also when there are contents

        elif page == "delete_server":
            if not permissions['Config'] in user_perms:
                if not exec_user['superuser']:
                    self.redirect("/panel/error?error=Unauthorized access to Config")    
                    return              
            server_id = self.get_argument('id', None)
            logger.info(
                "Removing server from panel for server: {}".format(self.controller.servers.get_server_friendly_name(server_id)))
            self.controller.remove_server(server_id, False)

        elif page == "delete_server_files":
            if not permissions['Config'] in user_perms:
                if not exec_user['superuser']:
                    self.redirect("/panel/error?error=Unauthorized access to Config")    
                    return              
            server_id = self.get_argument('id', None)
            logger.info(
                "Removing server and all associated files for server: {}".format(self.controller.servers.get_server_friendly_name(server_id)))
            self.controller.remove_server(server_id, True)

    @tornado.web.authenticated
    def put(self, page):
        user_data = json.loads(self.get_secure_cookie("user_data"))
        server_id = self.get_argument('id', None)
        exec_user_id = user_data['user_id']
        exec_user = helper_users.get_user(exec_user_id)
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
        if page == "save_file":
            if not permissions['Files'] in user_perms:
                if not exec_user['superuser']:
                    self.redirect("/panel/error?error=Unauthorized access to Files")    
                    return             
            file_contents = self.get_body_argument('file_contents', default=None, strip=True)
            file_path = helper.get_os_understandable_path(self.get_body_argument('file_path', default=None, strip=True))
            server_id = self.get_argument('id', None)

            if not self.check_server_id(server_id, 'save_file'): return
            else: server_id = bleach.clean(server_id)

            if not helper.in_path(helper.get_os_understandable_path(self.controller.servers.get_server_data_by_id(server_id)['path']), file_path)\
                or not helper.check_file_exists(os.path.abspath(file_path)):
                logger.warning("Invalid path in save_file ajax call ({})".format(file_path))
                console.warning("Invalid path in save_file ajax call ({})".format(file_path))
                return

            # Open the file in write mode and store the content in file_object
            with open(file_path, 'w') as file_object:
                file_object.write(file_contents)

        elif page == "rename_item":
            if not permissions['Files'] in user_perms:
                if not exec_user['superuser']:
                    self.redirect("/panel/error?error=Unauthorized access to Files")    
                    return  
            item_path = helper.get_os_understandable_path(self.get_body_argument('item_path', default=None, strip=True))
            new_item_name = self.get_body_argument('new_item_name', default=None, strip=True)
            server_id = self.get_argument('id', None)

            if not self.check_server_id(server_id, 'rename_item'): return
            else: server_id = bleach.clean(server_id)

            if item_path is None or new_item_name is None:
                logger.warning("Invalid path(s) in rename_item ajax call")
                console.warning("Invalid path(s) in rename_item ajax call")
                return

            if not helper.in_path(helper.get_os_understandable_path(self.controller.servers.get_server_data_by_id(server_id)['path']), item_path) \
                or not helper.check_path_exists(os.path.abspath(item_path)):
                logger.warning("Invalid old name path in rename_item ajax call ({})".format(server_id))
                console.warning("Invalid old name path in rename_item ajax call ({})".format(server_id))
                return

            new_item_path = os.path.join(os.path.split(item_path)[0], new_item_name)

            if not helper.in_path(helper.get_os_understandable_path(self.controller.servers.get_server_data_by_id(server_id)['path']), new_item_path) \
                or helper.check_path_exists(os.path.abspath(new_item_path)):
                logger.warning("Invalid new name path in rename_item ajax call ({})".format(server_id))
                console.warning("Invalid new name path in rename_item ajax call ({})".format(server_id))
                return

            # RENAME
            os.rename(item_path, new_item_path)

    def check_server_id(self, server_id, page_name):
        if server_id is None:
            logger.warning("Server ID not defined in {} ajax call ({})".format(page_name, server_id))
            console.warning("Server ID not defined in {} ajax call ({})".format(page_name, server_id))
            return
        else:
            server_id = bleach.clean(server_id)

            # does this server id exist?
            if not self.controller.servers.server_id_exists(server_id):
                logger.warning("Server ID not found in {} ajax call ({})".format(page_name, server_id))
                console.warning("Server ID not found in {} ajax call ({})".format(page_name, server_id))
                return
        return True
