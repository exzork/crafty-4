import os
import pathlib
import time
import logging
import shutil
import tempfile
from distutils import dir_util
from typing import Union
from peewee import DoesNotExist

from app.classes.controllers.crafty_perms_controller import Crafty_Perms_Controller
from app.classes.controllers.management_controller import Management_Controller
from app.classes.controllers.users_controller import Users_Controller
from app.classes.controllers.roles_controller import Roles_Controller
from app.classes.controllers.server_perms_controller import Server_Perms_Controller
from app.classes.controllers.servers_controller import Servers_Controller

from app.classes.models.server_permissions import Enum_Permissions_Server
from app.classes.models.users import helper_users
from app.classes.models.management import helpers_management
from app.classes.models.servers import servers_helper

from app.classes.shared.console import console
from app.classes.shared.helpers import helper
from app.classes.shared.server import Server

from app.classes.minecraft.server_props import ServerProps
from app.classes.minecraft.serverjars import server_jar_obj
from app.classes.minecraft.stats import Stats

from app.classes.web.websocket_helper import websocket_helper

logger = logging.getLogger(__name__)

class Controller:

    def __init__(self):
        self.servers_list = []
        self.stats = Stats(self)
        self.crafty_perms = Crafty_Perms_Controller()
        self.management = Management_Controller()
        self.roles = Roles_Controller()
        self.server_perms = Server_Perms_Controller()
        self.servers = Servers_Controller()
        self.users = Users_Controller()

    def check_server_loaded(self, server_id_to_check: int):

        logger.info(f"Checking to see if we already registered {server_id_to_check}")

        for s in self.servers_list:
            known_server = s.get('server_id')
            if known_server is None:
                return False

            if known_server == server_id_to_check:
                logger.info(f'skipping initialization of server {server_id_to_check} because it is already loaded')
                return True

        return False

    def init_all_servers(self):

        servers = self.servers.get_all_defined_servers()

        for s in servers:
            server_id = s.get('server_id')

            # if we have already initialized this server, let's skip it.
            if self.check_server_loaded(server_id):
                continue

            # if this server path no longer exists - let's warn and bomb out
            if not helper.check_path_exists(helper.get_os_understandable_path(s['path'])):
                logger.warning(f"Unable to find server {s['server_name']} at path {s['path']}. Skipping this server")

                console.warning(f"Unable to find server {s['server_name']} at path {s['path']}. Skipping this server")
                continue

            settings_file = os.path.join(helper.get_os_understandable_path(s['path']), 'server.properties')

            # if the properties file isn't there, let's warn
            if not helper.check_file_exists(settings_file):
                logger.error(f"Unable to find {settings_file}. Skipping this server.")
                console.error(f"Unable to find {settings_file}. Skipping this server.")
                continue

            settings = ServerProps(settings_file)

            temp_server_dict = {
                'server_id': s.get('server_id'),
                'server_data_obj': s,
                'server_obj': Server(self.stats),
                'server_settings': settings.props
            }

            # setup the server, do the auto start and all that jazz
            temp_server_dict['server_obj'].do_server_setup(s)

            # add this temp object to the list of init servers
            self.servers_list.append(temp_server_dict)

            if s['auto_start']:
                self.servers.set_waiting_start(s['server_id'], True)

            self.refresh_server_settings(s['server_id'])

            console.info(f"Loaded Server: ID {s['server_id']}" +
                         f" | Name: {s['server_name']}" +
                         f" | Autostart: {s['auto_start']}" +
                         f" | Delay: {s['auto_start_delay']} ")

    def refresh_server_settings(self, server_id: int):
        server_obj = self.get_server_obj(server_id)
        server_obj.reload_server_settings()

    @staticmethod
    def check_system_user():
        if helper_users.get_user_id_by_name("system") is not None:
            return True
        else:
            return False

    def set_project_root(self, root_dir):
        self.project_root = root_dir


    def package_support_logs(self, exec_user):
        #pausing so on screen notifications can run for user
        time.sleep(7)
        websocket_helper.broadcast_user(exec_user['user_id'], 'notification', 'Preparing your support logs')
        tempDir = tempfile.mkdtemp()
        tempZipStorage = tempfile.mkdtemp()
        full_temp = os.path.join(tempDir, 'support_logs')
        os.mkdir(full_temp)
        tempZipStorage = os.path.join(tempZipStorage, "support_logs")
        crafty_path = os.path.join(full_temp, "crafty")
        os.mkdir(crafty_path)
        server_path = os.path.join(full_temp, "server")
        os.mkdir(server_path)
        if exec_user['superuser']:
            auth_servers = self.servers.get_all_defined_servers()
        else:
            user_servers = self.servers.get_authorized_servers(int(exec_user['user_id']))
            auth_servers = []
            for server in user_servers:
                if Enum_Permissions_Server.Logs in self.server_perms.get_user_id_permissions_list(exec_user['user_id'], server["server_id"]):
                    auth_servers.append(server)
                else:
                    logger.info(f"Logs permission not available for server {server['server_name']}. Skipping.")
        #we'll iterate through our list of log paths from auth servers.
        for server in auth_servers:
            final_path = os.path.join(server_path, str(server['server_name']))
            os.mkdir(final_path)
            try:
                shutil.copy(server['log_path'], final_path)
            except Exception as e:
                logger.warning(f"Failed to copy file with error: {e}")
        #Copy crafty logs to archive dir
        full_log_name = os.path.join(crafty_path, 'logs')
        shutil.copytree(os.path.join(self.project_root, 'logs'), full_log_name)
        shutil.make_archive(tempZipStorage, "zip", tempDir)

        tempZipStorage += '.zip'
        websocket_helper.broadcast_user(exec_user['user_id'], 'send_logs_bootbox', {
                })

        self.users.set_support_path(exec_user['user_id'], tempZipStorage)

    @staticmethod
    def add_system_user():
        helper_users.add_user("system", helper.random_string_generator(64), "default@example.com", False, False)

    def get_server_settings(self, server_id):
        for s in self.servers_list:
            if int(s['server_id']) == int(server_id):
                return s['server_settings']

        logger.warning(f"Unable to find server object for server id {server_id}")
        return False

    def get_server_obj(self, server_id: Union[str, int]) -> Union[bool, Server]:
        for s in self.servers_list:
            if str(s['server_id']) == str(server_id):
                return s['server_obj']

        logger.warning(f"Unable to find server object for server id {server_id}")
        return False  # TODO: Change to None

    def get_server_data(self, server_id: str):
        for s in self.servers_list:
            if str(s['server_id']) == str(server_id):
                return s['server_data_obj']

        logger.warning(f"Unable to find server object for server id {server_id}")
        return False

    @staticmethod
    def list_defined_servers():
        servers = servers_helper.get_all_defined_servers()
        return servers

    def list_running_servers(self):
        running_servers = []

        # for each server
        for s in self.servers_list:

            # is the server running?
            srv_obj = s['server_obj']
            running = srv_obj.check_running()
            # if so, let's add a dictionary to the list of running servers
            if running:
                running_servers.append({
                    'id': srv_obj.server_id,
                    'name': srv_obj.name
                })

        return running_servers

    def stop_all_servers(self):
        servers = self.list_running_servers()
        logger.info(f"Found {len(servers)} running server(s)")
        console.info(f"Found {len(servers)} running server(s)")

        logger.info("Stopping All Servers")
        console.info("Stopping All Servers")

        for s in servers:
            logger.info(f"Stopping Server ID {s['id']} - {s['name']}")
            console.info(f"Stopping Server ID {s['id']} - {s['name']}")

            self.stop_server(s['id'])

            # let's wait 2 seconds to let everything flush out
            time.sleep(2)

        logger.info("All Servers Stopped")
        console.info("All Servers Stopped")

    def stop_server(self, server_id):
        # issue the stop command
        svr_obj = self.get_server_obj(server_id)
        svr_obj.stop_threaded_server()

    def create_jar_server(self, server: str, version: str, name: str, min_mem: int, max_mem: int, port: int):
        server_id = helper.create_uuid()
        server_dir = os.path.join(helper.servers_dir, server_id)
        backup_path = os.path.join(helper.backup_path, server_id)
        if helper.is_os_windows():
            server_dir = helper.wtol_path(server_dir)
            backup_path = helper.wtol_path(backup_path)
            server_dir.replace(' ', '^ ')
            backup_path.replace(' ', '^ ')

        server_file = f"{server}-{version}.jar"
        full_jar_path = os.path.join(server_dir, server_file)

        # make the dir - perhaps a UUID?
        helper.ensure_dir_exists(server_dir)
        helper.ensure_dir_exists(backup_path)

        try:
            # do a eula.txt
            with open(os.path.join(server_dir, "eula.txt"), 'w', encoding='utf-8') as f:
                f.write("eula=false")
                f.close()

            # setup server.properties with the port
            with open(os.path.join(server_dir, "server.properties"), "w", encoding='utf-8') as f:
                f.write(f"server-port={port}")
                f.close()

        except Exception as e:
            logger.error(f"Unable to create required server files due to :{e}")
            return False

        #must remain non-fstring due to string addtion
        if helper.is_os_windows():
            server_command = f'java -Xms{helper.float_to_string(min_mem)}M -Xmx{helper.float_to_string(max_mem)}M -jar "{full_jar_path}" nogui'
        else:
            server_command = f'java -Xms{helper.float_to_string(min_mem)}M -Xmx{helper.float_to_string(max_mem)}M -jar {full_jar_path} nogui'
        server_log_file = f"{server_dir}/logs/latest.log"
        server_stop = "stop"

        # download the jar
        server_jar_obj.download_jar(server, version, full_jar_path)

        new_id = self.register_server(name, server_id, server_dir, backup_path, server_command, server_file, server_log_file, server_stop, port)
        return new_id

    @staticmethod
    def verify_jar_server( server_path: str, server_jar: str):
        server_path = helper.get_os_understandable_path(server_path)
        path_check = helper.check_path_exists(server_path)
        jar_check = helper.check_file_exists(os.path.join(server_path, server_jar))
        if not path_check or not jar_check:
            return False
        return True

    @staticmethod
    def verify_zip_server(zip_path: str):
        zip_path = helper.get_os_understandable_path(zip_path)
        zip_check = helper.check_file_exists(zip_path)
        if not zip_check:
            return False
        return True

    def import_jar_server(self, server_name: str, server_path: str, server_jar: str, min_mem: int, max_mem: int, port: int):
        server_id = helper.create_uuid()
        new_server_dir = os.path.join(helper.servers_dir, server_id)
        backup_path = os.path.join(helper.backup_path, server_id)
        if helper.is_os_windows():
            new_server_dir = helper.wtol_path(new_server_dir)
            backup_path = helper.wtol_path(backup_path)
            new_server_dir.replace(' ', '^ ')
            backup_path.replace(' ', '^ ')

        helper.ensure_dir_exists(new_server_dir)
        helper.ensure_dir_exists(backup_path)
        server_path = helper.get_os_understandable_path(server_path)
        dir_util.copy_tree(server_path, new_server_dir)

        has_properties = False
        for item in os.listdir(new_server_dir):
            if str(item) == 'server.properties':
                has_properties = True
        if not has_properties:
            logger.info(f"No server.properties found on zip file import. Creating one with port selection of {str(port)}")
            with open(os.path.join(new_server_dir, "server.properties"), "w", encoding='utf-8') as f:
                f.write(f"server-port={port}")
                f.close()

        full_jar_path = os.path.join(new_server_dir, server_jar)

        #due to adding strings this must not be an fstring
        if helper.is_os_windows():
            server_command = f'java -Xms{helper.float_to_string(min_mem)}M -Xmx{helper.float_to_string(max_mem)}M -jar "{full_jar_path}" nogui'
        else:
            server_command = f'java -Xms{helper.float_to_string(min_mem)}M -Xmx{helper.float_to_string(max_mem)}M -jar {full_jar_path} nogui'
        server_log_file = f"{new_server_dir}/logs/latest.log"
        server_stop = "stop"

        new_id = self.register_server(server_name, server_id, new_server_dir, backup_path, server_command, server_jar,
                                      server_log_file, server_stop, port)
        return new_id

    def import_zip_server(self, server_name: str, zip_path: str, server_jar: str, min_mem: int, max_mem: int, port: int):
        server_id = helper.create_uuid()
        new_server_dir = os.path.join(helper.servers_dir, server_id)
        backup_path = os.path.join(helper.backup_path, server_id)
        if helper.is_os_windows():
            new_server_dir = helper.wtol_path(new_server_dir)
            backup_path = helper.wtol_path(backup_path)
            new_server_dir.replace(' ', '^ ')
            backup_path.replace(' ', '^ ')

        tempDir = helper.get_os_understandable_path(zip_path)
        helper.ensure_dir_exists(new_server_dir)
        helper.ensure_dir_exists(backup_path)
        has_properties = False
        #extracts archive to temp directory
        for item in os.listdir(tempDir):
            if str(item) == 'server.properties':
                has_properties = True
            try:
                shutil.move(os.path.join(tempDir, item), os.path.join(new_server_dir, item))
            except Exception as ex:
                logger.error(f'ERROR IN ZIP IMPORT: {ex}')
        if not has_properties:
            logger.info(f"No server.properties found on zip file import. Creating one with port selection of {str(port)}")
            with open(os.path.join(new_server_dir, "server.properties"), "w", encoding='utf-8') as f:
                f.write(f"server-port={port}")
                f.close()

        full_jar_path = os.path.join(new_server_dir, server_jar)

        #due to strings being added we need to leave this as not an fstring
        if helper.is_os_windows():
            server_command = f'java -Xms{helper.float_to_string(min_mem)}M -Xmx{helper.float_to_string(max_mem)}M -jar "{full_jar_path}" nogui'
        else:
            server_command = f'java -Xms{helper.float_to_string(min_mem)}M -Xmx{helper.float_to_string(max_mem)}M -jar {full_jar_path} nogui'
        logger.debug('command: ' + server_command)
        server_log_file = f"{new_server_dir}/logs/latest.log"
        server_stop = "stop"

        new_id = self.register_server(server_name, server_id, new_server_dir, backup_path, server_command, server_jar,
                                      server_log_file, server_stop, port)
        return new_id

    def rename_backup_dir(self, old_server_id, new_server_id, new_uuid):
        server_data = self.servers.get_server_data_by_id(old_server_id)
        old_bu_path = server_data['backup_path']
        Server_Perms_Controller.backup_role_swap(old_server_id, new_server_id)
        backup_path = helper.validate_traversal(helper.backup_path, old_bu_path)
        if helper.is_os_windows():
            backup_path = helper.wtol_path(backup_path)
            backup_path.replace(' ', '^ ')
        backup_path_components = list(backup_path.parts)
        backup_path_components[-1] = new_uuid
        new_bu_path = pathlib.PurePath(os.path.join(*backup_path_components))
        if os.path.isdir(new_bu_path):
            if helper.validate_traversal(helper.backup_path, new_bu_path):
                os.rmdir(new_bu_path)
        backup_path.rename(new_bu_path)

    def register_server(self, name: str,
                        server_uuid: str,
                        server_dir: str,
                        backup_path: str,
                        server_command: str,
                        server_file: str,
                        server_log_file: str,
                        server_stop: str,
                        server_port: int):
        # put data in the db

        new_id = self.servers.create_server(
            name, server_uuid, server_dir, backup_path, server_command, server_file, server_log_file, server_stop, server_port)

        if not helper.check_file_exists(os.path.join(server_dir, "crafty_managed.txt")):
            try:
                # place a file in the dir saying it's owned by crafty
                with open(os.path.join(server_dir, "crafty_managed.txt"), 'w', encoding='utf-8') as f:
                    f.write(
                        "The server is managed by Crafty Controller.\n Leave this directory/files alone please")
                    f.close()

            except Exception as e:
                logger.error(f"Unable to create required server files due to :{e}")
                return False

        # let's re-init all servers
        self.init_all_servers()

        return new_id

    def remove_server(self, server_id, files):
        counter = 0
        for s in self.servers_list:

            # if this is the droid... im mean server we are looking for...
            if str(s['server_id']) == str(server_id):
                server_data = self.get_server_data(server_id)
                server_name = server_data['server_name']

                logger.info(f"Deleting Server: ID {server_id} | Name: {server_name} ")
                console.info(f"Deleting Server: ID {server_id} | Name: {server_name} ")

                srv_obj = s['server_obj']
                running = srv_obj.check_running()

                if running:
                    self.stop_server(server_id)
                if files:
                    try:
                        shutil.rmtree(helper.get_os_understandable_path(self.servers.get_server_data_by_id(server_id)['path']))
                    except Exception as e:
                        logger.error(f"Unable to delete server files for server with ID: {server_id} with error logged: {e}")
                    if helper.check_path_exists(self.servers.get_server_data_by_id(server_id)['backup_path']):
                        shutil.rmtree(helper.get_os_understandable_path(self.servers.get_server_data_by_id(server_id)['backup_path']))


                #Cleanup scheduled tasks
                try:
                    helpers_management.delete_scheduled_task_by_server(server_id)
                except DoesNotExist:
                    logger.info("No scheduled jobs exist. Continuing.")
                # remove the server from the DB
                self.servers.remove_server(server_id)

                # remove the server from servers list
                self.servers_list.pop(counter)

            counter += 1
