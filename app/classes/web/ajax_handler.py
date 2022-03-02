import os
import html
import re
import logging
import time
import tornado.web
import tornado.escape
import bleach

from app.classes.shared.console import console
from app.classes.shared.helpers import helper
from app.classes.web.websocket_helper import websocket_helper
from app.classes.shared.translation import translation
from app.classes.shared.server import ServerOutBuf

from app.classes.web.base_handler import BaseHandler
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
        _, _, exec_user = self.current_user
        error = bleach.clean(self.get_argument('error', "WTF Error!"))

        template = "panel/denied.html"

        page_data = {
            'user_data': exec_user,
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
                logger.warning(f"Log path not found in server_log ajax call ({server_id})")

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
                    self.write(f'{line}<br />')
                    # self.write(d.encode("utf-8"))

                except Exception as e:
                    logger.warning(f"Skipping Log Line due to error: {e}")

        elif page == "announcements":
            data = helper.get_announcements()
            page_data['notify_data'] = data
            self.render_page('ajax/notify.html', page_data)


        elif page == "get_zip_tree":
            path = self.get_argument('path', None)

            self.write(helper.get_os_understandable_path(path) + '\n' +
                        helper.generate_zip_tree(path))
            self.finish()

        elif page == "get_zip_dir":
            path = self.get_argument('path', None)

            self.write(helper.get_os_understandable_path(path) + '\n' +
                        helper.generate_zip_dir(path))
            self.finish()

        elif page == "get_backup_tree":
            server_id = self.get_argument('id', None)
            folder = self.get_argument('path', None)

            output = ""

            dir_list = []
            unsorted_files = []
            file_list = os.listdir(folder)
            for item in file_list:
                if os.path.isdir(os.path.join(folder, item)):
                    dir_list.append(item)
                else:
                    unsorted_files.append(item)
            file_list = sorted(dir_list, key=str.casefold) + sorted(unsorted_files, key=str.casefold)
            output += \
        f"""<ul class="tree-nested d-block" id="{folder}ul">"""\

            for raw_filename in file_list:
                filename = html.escape(raw_filename)
                rel = os.path.join(folder, raw_filename)
                dpath = os.path.join(folder, filename)
                if str(dpath) in self.controller.management.get_excluded_backup_dirs(server_id):
                    if os.path.isdir(rel):
                        output += \
                            f"""<li class="tree-item" data-path="{dpath}">
                            \n<div id="{dpath}" data-path="{dpath}" data-name="{filename}" class="tree-caret tree-ctx-item tree-folder">
                            <input type="checkbox" class="checkBoxClass" name="root_path" value="{dpath}" checked>
                            <span id="{dpath}span" class="files-tree-title" data-path="{dpath}" data-name="{filename}" onclick="getDirView(event)">
                            <i class="far fa-folder"></i>
                            <i class="far fa-folder-open"></i>
                            <strong>{filename}</strong>
                            </span>
                            </input></div><li>
                            \n"""\

                    else:
                        output += f"""<li
                        class="tree-nested d-block tree-ctx-item tree-file"
                        data-path="{dpath}"
                        data-name="{filename}"
                        onclick=""><input type='checkbox' class="checkBoxClass" name='root_path' value="{dpath}" checked><span style="margin-right: 6px;">
                        <i class="far fa-file"></i></span></input>{filename}</li>"""

                else:
                    if os.path.isdir(rel):
                        output += \
                            f"""<li class="tree-item" data-path="{dpath}">
                            \n<div id="{dpath}" data-path="{dpath}" data-name="{filename}" class="tree-caret tree-ctx-item tree-folder">
                            <input type="checkbox" class="checkBoxClass" name="root_path" value="{dpath}">
                            <span id="{dpath}span" class="files-tree-title" data-path="{dpath}" data-name="{filename}" onclick="getDirView(event)">
                            <i class="far fa-folder"></i>
                            <i class="far fa-folder-open"></i>
                            <strong>{filename}</strong>
                            </span>
                            </input></div><li>
                            \n"""\

                    else:
                        output += f"""<li
                        class="tree-nested d-block tree-ctx-item tree-file"
                        data-path="{dpath}"
                        data-name="{filename}"
                        onclick=""><input type='checkbox' class="checkBoxClass" name='root_path' value="{dpath}">
                        <span style="margin-right: 6px;"><i class="far fa-file"></i></span></input>{filename}</li>"""
            self.write(helper.get_os_understandable_path(folder) + '\n' +
                        output)
            self.finish()

        elif page == "get_backup_dir":
            server_id = self.get_argument('id', None)
            folder = self.get_argument('path', None)
            output = ""

            dir_list = []
            unsorted_files = []
            file_list = os.listdir(folder)
            for item in file_list:
                if os.path.isdir(os.path.join(folder, item)):
                    dir_list.append(item)
                else:
                    unsorted_files.append(item)
            file_list = sorted(dir_list, key=str.casefold) + sorted(unsorted_files, key=str.casefold)
            output += \
        f"""<ul class="tree-nested d-block" id="{folder}ul">"""\

            for raw_filename in file_list:
                filename = html.escape(raw_filename)
                rel = os.path.join(folder, raw_filename)
                dpath = os.path.join(folder, filename)
                if str(dpath) in self.controller.management.get_excluded_backup_dirs(server_id):
                    if os.path.isdir(rel):
                        output += \
                            f"""<li class="tree-item" data-path="{dpath}">
                            \n<div id="{dpath}" data-path="{dpath}" data-name="{filename}" class="tree-caret tree-ctx-item tree-folder">
                            <input type="checkbox" name="root_path" value="{dpath}">
                            <span id="{dpath}span" class="files-tree-title" data-path="{dpath}" data-name="{filename}" onclick="getDirView(event)">
                            <i class="far fa-folder"></i>
                            <i class="far fa-folder-open"></i>
                            <strong>{filename}</strong>
                            </span>
                            </input></div><li>"""\

                    else:
                        output += f"""<li
                        class="tree-item tree-ctx-item tree-file"
                        data-path="{dpath}"
                        data-name="{filename}"
                        onclick=""><input type='checkbox' name='root_path' value='{dpath}'><span style="margin-right: 6px;">
                        <i class="far fa-file"></i></span></input>{filename}</li>"""

                else:
                    if os.path.isdir(rel):
                        output += \
                            f"""<li class="tree-item" data-path="{dpath}">
                            \n<div id="{dpath}" data-path="{dpath}" data-name="{filename}" class="tree-caret tree-ctx-item tree-folder">
                            <input type="checkbox" name="root_path" value="{dpath}">
                            <span id="{dpath}span" class="files-tree-title" data-path="{dpath}" data-name="{filename}" onclick="getDirView(event)">
                            <i class="far fa-folder"></i>
                            <i class="far fa-folder-open"></i>
                            <strong>{filename}</strong>
                            </span>
                            </input></div><li>"""\

                    else:
                        output += f"""<li
                        class="tree-item tree-ctx-item tree-file"
                        data-path="{dpath}"
                        data-name="{filename}"
                        onclick=""><input type='checkbox' name='root_path' value='{dpath}'>
                        <span style="margin-right: 6px;"><i class="far fa-file"></i></span></input>{filename}</li>"""

            self.write(helper.get_os_understandable_path(folder) + '\n' +
                        output)
            self.finish()

        elif page == "get_dir":
            server_id = self.get_argument('id', None)
            path = self.get_argument('path', None)

            if not self.check_server_id(server_id, 'get_tree'):
                return
            else:
                server_id = bleach.clean(server_id)

            if helper.validate_traversal(self.controller.servers.get_server_data_by_id(server_id)['path'], path):
                self.write(helper.get_os_understandable_path(path) + '\n' +
                        helper.generate_dir(path))
            self.finish()

    @tornado.web.authenticated
    def post(self, page):
        api_key, _, exec_user = self.current_user
        superuser = exec_user['superuser']
        if api_key is not None:
            superuser = superuser and api_key.superuser

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
        user_perms = self.controller.server_perms.get_user_id_permissions_list(exec_user['user_id'], server_id)

        if page == "send_command":
            command = self.get_body_argument('command', default=None, strip=True)
            server_id = self.get_argument('id', None)

            if server_id is None:
                logger.warning("Server ID not found in send_command ajax call")
                console.warning("Server ID not found in send_command ajax call")

            srv_obj = self.controller.get_server_obj(server_id)

            if command == srv_obj.settings['stop_command']:
                logger.info("Stop command detected as terminal input - intercepting." +
                            f"Starting Crafty's stop process for server with id: {server_id}")
                self.controller.management.send_command(exec_user['user_id'], server_id, self.get_remote_ip(), 'stop_server')
                command = None
            elif command == 'restart':
                logger.info("Restart command detected as terminal input - intercepting." +
                            f"Starting Crafty's stop process for server with id: {server_id}")
                self.controller.management.send_command(exec_user['user_id'], server_id, self.get_remote_ip(), 'restart_server')
                command = None
            if command:
                if srv_obj.check_running():
                    srv_obj.send_command(command)

            self.controller.management.add_to_audit_log(exec_user['user_id'],
                                        f"Sent command to {self.controller.servers.get_server_friendly_name(server_id)} terminal: {command}",
                                        server_id,
                                        self.get_remote_ip())

        elif page == "send_order":
            self.controller.users.update_server_order(exec_user['user_id'], bleach.clean(self.get_argument('order')))
            return

        elif page == "kill":
            if not permissions['Commands'] in user_perms:
                if not superuser:
                    self.redirect("/panel/error?error=Unauthorized access to Commands")
                    return
            server_id = self.get_argument('id', None)
            svr = self.controller.get_server_obj(server_id)
            try:
                svr.kill()
            except Exception as e:
                logger.error(f"Could not find PID for requested termsig. Full error: {e}")
            return
        elif page == "eula":
            server_id = self.get_argument('id', None)
            svr = self.controller.get_server_obj(server_id)
            svr.agree_eula(exec_user['user_id'])

        elif page == "restore_backup":
            if not permissions['Backup'] in user_perms:
                if not superuser:
                    self.redirect("/panel/error?error=Unauthorized access to Backups")
                    return
            server_id = bleach.clean(self.get_argument('id', None))
            zip_name = bleach.clean(self.get_argument('zip_file', None))
            svr_obj = self.controller.servers.get_server_obj(server_id)
            server_data = self.controller.servers.get_server_data_by_id(server_id)
            backup_path = svr_obj.backup_path
            if helper.validate_traversal(backup_path, zip_name):
                tempDir = helper.unzip_backup_archive(backup_path, zip_name)
                new_server = self.controller.import_zip_server(svr_obj.server_name,
                                                               tempDir,
                                                               server_data['executable'],
                                                               '1', '2',
                                                               server_data['server_port'])
                new_server_id = new_server
                new_server = self.controller.get_server_data(new_server)
                self.controller.rename_backup_dir(server_id, new_server_id, new_server['server_uuid'])
                self.controller.remove_server(server_id, True)
                self.redirect('/panel/dashboard')

        elif page == "unzip_server":
            path = self.get_argument('path', None)
            if helper.check_file_exists(path):
                helper.unzipServer(path, exec_user['user_id'])
            else:
                user_id = exec_user['user_id']
                if user_id:
                    time.sleep(5)
                    user_lang = self.controller.users.get_user_lang_by_id(user_id)
                    websocket_helper.broadcast_user(user_id, 'send_start_error',{
                    'error': translation.translate('error', 'no-file', user_lang)
                })
            return

        elif page == "backup_select":
            path = self.get_argument('path', None)
            helper.backup_select(path, exec_user['user_id'])
            return


    @tornado.web.authenticated
    def delete(self, page):
        api_key, _, exec_user = self.current_user
        superuser = exec_user['superuser']
        if api_key is not None:
            superuser = superuser and api_key.superuser

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
        user_perms = self.controller.server_perms.get_user_id_permissions_list(exec_user['user_id'], server_id)
        if page == "del_task":
            if not permissions['Schedule'] in user_perms:
                self.redirect("/panel/error?error=Unauthorized access to Tasks")
            else:
                sch_id = self.get_argument('schedule_id', '-404')
                self.tasks_manager.remove_job(sch_id)

        if page == "del_backup":
            if not permissions['Backup'] in user_perms:
                if not superuser:
                    self.redirect("/panel/error?error=Unauthorized access to Backups")
                    return
            file_path = helper.get_os_understandable_path(self.get_body_argument('file_path', default=None, strip=True))
            server_id = self.get_argument('id', None)

            console.warning(f"Delete {file_path} for server {server_id}")

            if not self.check_server_id(server_id, 'del_backup'):
                return
            else: server_id = bleach.clean(server_id)

            server_info = self.controller.servers.get_server_data_by_id(server_id)
            if not (helper.in_path(helper.get_os_understandable_path(server_info['path']), file_path) \
                or helper.in_path(helper.get_os_understandable_path(server_info['backup_path']), file_path)) \
                or not helper.check_file_exists(os.path.abspath(file_path)):
                logger.warning(f"Invalid path in del_backup ajax call ({file_path})")
                console.warning(f"Invalid path in del_backup ajax call ({file_path})")
                return

            # Delete the file
            if helper.validate_traversal(helper.get_os_understandable_path(server_info['backup_path']), file_path):
                os.remove(file_path)

        elif page == "delete_server":
            if not permissions['Config'] in user_perms:
                if not superuser:
                    self.redirect("/panel/error?error=Unauthorized access to Config")
                    return
            server_id = self.get_argument('id', None)
            logger.info(f"Removing server from panel for server: {self.controller.servers.get_server_friendly_name(server_id)}")

            server_data = self.controller.get_server_data(server_id)
            server_name = server_data['server_name']

            self.controller.management.add_to_audit_log(exec_user['user_id'],
                                       f"Deleted server {server_id} named {server_name}",
                                       server_id,
                                       self.get_remote_ip())

            self.tasks_manager.remove_all_server_tasks(server_id)
            self.controller.remove_server(server_id, False)

        elif page == "delete_server_files":
            if not permissions['Config'] in user_perms:
                if not superuser:
                    self.redirect("/panel/error?error=Unauthorized access to Config")
                    return
            server_id = self.get_argument('id', None)
            logger.info(f"Removing server and all associated files for server: {self.controller.servers.get_server_friendly_name(server_id)}")

            server_data = self.controller.get_server_data(server_id)
            server_name = server_data['server_name']

            self.controller.management.add_to_audit_log(exec_user['user_id'],
                                       f"Deleted server {server_id} named {server_name}",
                                       server_id,
                                       self.get_remote_ip())

            self.tasks_manager.remove_all_server_tasks(server_id)
            self.controller.remove_server(server_id, True)

    def check_server_id(self, server_id, page_name):
        if server_id is None:
            logger.warning(f"Server ID not defined in {page_name} ajax call ({server_id})")
            console.warning(f"Server ID not defined in {page_name} ajax call ({server_id})")
            return
        else:
            server_id = bleach.clean(server_id)

            # does this server id exist?
            if not self.controller.servers.server_id_exists(server_id):
                logger.warning(f"Server ID not found in {page_name} ajax call ({server_id})")
                console.warning(f"Server ID not found in {page_name} ajax call ({server_id})")
                return
        return True
