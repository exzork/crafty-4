import json
import logging
import tornado.web
import tornado.escape
import bleach
import os
import shutil

from app.classes.shared.console import console
from app.classes.shared.models import Users, installer
from app.classes.web.base_handler import BaseHandler
from app.classes.shared.controller import controller
from app.classes.shared.models import db_helper
from app.classes.shared.helpers import helper

logger = logging.getLogger(__name__)


class AjaxHandler(BaseHandler):

    def render_page(self, template, page_data):
        self.render(
            template,
            data=page_data
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
                return False

            server_id = bleach.clean(server_id)

            server_data = db_helper.get_server_data_by_id(server_id)
            if not server_data:
                logger.warning("Server Data not found in server_log ajax call")
                self.redirect("/panel/error?error=Server ID Not Found")

            if server_data['log_path']:
                logger.warning("Server ID not found in server_log ajax call")

            if full_log:
                log_lines = helper.get_setting('max_log_lines')
            else:
                log_lines = helper.get_setting('virtual_terminal_lines')

            data = helper.tail_file(server_data['log_path'], log_lines)

            for d in data:
                try:
                    line = helper.log_colors(d)
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
            file_path = self.get_argument('file_path', None)
            server_id = self.get_argument('id', None)

            if server_id is None:
                logger.warning("Server ID not found in get_file ajax call")
                console.warning("Server ID not found in get_file ajax call")
                return False
            else:
                server_id = bleach.clean(server_id)

                # does this server id exist?
                if not db_helper.server_id_exists(server_id):
                    logger.warning("Server ID not found in get_file ajax call")
                    console.warning("Server ID not found in get_file ajax call")
                    return False

            if not helper.in_path(db_helper.get_server_data_by_id(server_id)['path'], file_path)\
                    or not helper.check_file_exists(os.path.abspath(file_path)):
                logger.warning("Invalid path in get_file ajax call")
                console.warning("Invalid path in get_file ajax call")
                return False

            file = open(file_path)
            file_contents = file.read()
            file.close()

            console.debug("Send file contents")
            self.write(file_contents)
            self.finish()

        elif page == "get_tree":
            server_id = self.get_argument('id', None)

            if server_id is None:
                logger.warning("Server ID not found in get_file ajax call")
                console.warning("Server ID not found in get_file ajax call")
                return False
            else:
                server_id = bleach.clean(server_id)

                # does this server id exist?
                if not db_helper.server_id_exists(server_id):
                    logger.warning("Server ID not found in get_file ajax call")
                    console.warning("Server ID not found in get_file ajax call")
                    return False

            self.write(db_helper.get_server_data_by_id(server_id)['path'] + '\n' +
                       helper.generate_tree(db_helper.get_server_data_by_id(server_id)['path']))
            self.finish()

    @tornado.web.authenticated
    def post(self, page):
        user_data = json.loads(self.get_secure_cookie("user_data"))
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

            srv_obj = controller.get_server_obj(server_id)

            if command:
                if srv_obj.check_running():
                    srv_obj.send_command(command)

        elif page == "create_file":
            file_parent = self.get_body_argument('file_parent', default=None, strip=True)
            file_name = self.get_body_argument('file_name', default=None, strip=True)
            file_path = os.path.join(file_parent, file_name)
            server_id = self.get_argument('id', None)
            print(server_id)

            if server_id is None:
                logger.warning("Server ID not found in create_file ajax call")
                console.warning("Server ID not found in create_file ajax call")
                return False
            else:
                server_id = bleach.clean(server_id)

                # does this server id exist?
                if not db_helper.server_id_exists(server_id):
                    logger.warning("Server ID not found in create_file ajax call")
                    console.warning("Server ID not found in create_file ajax call")
                    return False

            if not helper.in_path(db_helper.get_server_data_by_id(server_id)['path'], file_path) \
                    or helper.check_file_exists(os.path.abspath(file_path)):
                logger.warning("Invalid path in create_file ajax call")
                console.warning("Invalid path in create_file ajax call")
                return False

            # Create the file by opening it
            with open(file_path, 'w') as file_object:
                file_object.close()

        elif page == "create_dir":
            dir_parent = self.get_body_argument('dir_parent', default=None, strip=True)
            dir_name = self.get_body_argument('dir_name', default=None, strip=True)
            dir_path = os.path.join(dir_parent, dir_name)
            server_id = self.get_argument('id', None)
            print(server_id)

            if server_id is None:
                logger.warning("Server ID not found in create_dir ajax call")
                console.warning("Server ID not found in create_dir ajax call")
                return False
            else:
                server_id = bleach.clean(server_id)

                # does this server id exist?
                if not db_helper.server_id_exists(server_id):
                    logger.warning("Server ID not found in create_dir ajax call")
                    console.warning("Server ID not found in create_dir ajax call")
                    return False

            if not helper.in_path(db_helper.get_server_data_by_id(server_id)['path'], dir_path) \
                    or helper.check_path_exists(os.path.abspath(dir_path)):
                logger.warning("Invalid path in create_dir ajax call")
                console.warning("Invalid path in create_dir ajax call")
                return False

            # Create the directory
            os.mkdir(dir_path)

    @tornado.web.authenticated
    def delete(self, page):
        if page == "del_file":
            file_path = self.get_body_argument('file_path', default=None, strip=True)
            server_id = self.get_argument('id', None)
            print(server_id)

            if server_id is None:
                logger.warning("Server ID not found in del_file ajax call")
                console.warning("Server ID not found in del_file ajax call")
                return False
            else:
                server_id = bleach.clean(server_id)

                # does this server id exist?
                if not db_helper.server_id_exists(server_id):
                    logger.warning("Server ID not found in del_file ajax call")
                    console.warning("Server ID not found in del_file ajax call")
                    return False

            if not helper.in_path(db_helper.get_server_data_by_id(server_id)['path'], file_path) \
                    or not helper.check_file_exists(os.path.abspath(file_path)):
                logger.warning("Invalid path in del_file ajax call")
                console.warning("Invalid path in del_file ajax call")
                return False

            # Delete the file
            os.remove(file_path)

        elif page == "del_dir":
            dir_path = self.get_body_argument('dir_path', default=None, strip=True)
            server_id = self.get_argument('id', None)
            print(server_id)

            if server_id is None:
                logger.warning("Server ID not found in del_file ajax call")
                console.warning("Server ID not found in del_file ajax call")
                return False
            else:
                server_id = bleach.clean(server_id)

                # does this server id exist?
                if not db_helper.server_id_exists(server_id):
                    logger.warning("Server ID not found in del_file ajax call")
                    console.warning("Server ID not found in del_file ajax call")
                    return False

            if not helper.in_path(db_helper.get_server_data_by_id(server_id)['path'], dir_path) \
                    or not helper.check_path_exists(os.path.abspath(dir_path)):
                logger.warning("Invalid path in del_file ajax call")
                console.warning("Invalid path in del_file ajax call")
                return False

            # Delete the file
            # os.rmdir(dir_path)
            shutil.rmtree(dir_path)  # Removes also when there are contents

    @tornado.web.authenticated
    def put(self, page):
        if page == "save_file":
            file_contents = self.get_body_argument('file_contents', default=None, strip=True)
            file_path = self.get_body_argument('file_path', default=None, strip=True)
            server_id = self.get_argument('id', None)
            print(file_contents)
            print(file_path)
            print(server_id)

            if server_id is None:
                logger.warning("Server ID not found in save_file ajax call")
                console.warning("Server ID not found in save_file ajax call")
                return False
            else:
                server_id = bleach.clean(server_id)

                # does this server id exist?
                if not db_helper.server_id_exists(server_id):
                    logger.warning("Server ID not found in save_file ajax call")
                    console.warning("Server ID not found in save_file ajax call")
                    return False

            if not helper.in_path(db_helper.get_server_data_by_id(server_id)['path'], file_path)\
                    or not helper.check_file_exists(os.path.abspath(file_path)):
                logger.warning("Invalid path in save_file ajax call")
                console.warning("Invalid path in save_file ajax call")
                return False

            # Open the file in write mode and store the content in file_object
            with open(file_path, 'w') as file_object:
                file_object.write(file_contents)

        elif page == "rename_item":
            item_path = self.get_body_argument('item_path', default=None, strip=True)
            new_item_name = self.get_body_argument('new_item_name', default=None, strip=True)
            server_id = self.get_argument('id', None)
            print(server_id)

            if server_id is None:
                logger.warning("Server ID not found in rename_item ajax call")
                console.warning("Server ID not found in rename_item ajax call")
                return False
            else:
                server_id = bleach.clean(server_id)

                # does this server id exist?
                if not db_helper.server_id_exists(server_id):
                    logger.warning("Server ID not found in rename_item ajax call (1)")
                    console.warning("Server ID not found in rename_item ajax call (1)")
                    return False

            if item_path is None or new_item_name is None:
                logger.warning("Invalid path in rename_item ajax call (2)")
                console.warning("Invalid path in rename_item ajax call (2)")
                return False

            if not helper.in_path(db_helper.get_server_data_by_id(server_id)['path'], item_path) \
                    or not helper.check_path_exists(os.path.abspath(item_path)):
                logger.warning("Invalid path in rename_item ajax call (3)")
                console.warning("Invalid path in rename_item ajax call (3)")
                return False

            new_item_path = os.path.join(os.path.split(item_path)[0], new_item_name)

            if not helper.in_path(db_helper.get_server_data_by_id(server_id)['path'], new_item_path) \
                    or helper.check_path_exists(os.path.abspath(new_item_path)):
                logger.warning("Invalid path 2 in rename_item ajax call")
                console.warning("Invalid path 2 in rename_item ajax call")
                return False

            # RENAME
            os.rename(item_path, new_item_path)
