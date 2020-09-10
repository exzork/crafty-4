import os
import time
import logging
import sys
import yaml

from app.classes.shared.helpers import helper
from app.classes.shared.console import console

from app.classes.shared.models import db_helper, Servers

from app.classes.shared.server import Server
from app.classes.minecraft.server_props import ServerProps
from app.classes.minecraft.serverjars import server_jar_obj

logger = logging.getLogger(__name__)


class Controller:

    def __init__(self):
        self.servers_list = []

    def init_all_servers(self):

        # if we have servers defined, let's destroy it and start over
        if len(self.servers_list) > 0:
            self.servers_list = []

        servers = db_helper.get_all_defined_servers()

        for s in servers:

            # if this server path no longer exists - let's warn and bomb out
            if not helper.check_path_exits(s['path']):
                logger.warning("Unable to find server {} at path {}. Skipping this server".format(s['server_name'],
                                                                                                  s['path']))

                console.warning("Unable to find server {} at path {}. Skipping this server".format(s['server_name'],
                                                                                                   s['path']))
                continue

            settings_file = os.path.join(s['path'], 'server.properties')

            # if the properties file isn't there, let's warn
            if not helper.check_file_exists(settings_file):
                logger.error("Unable to find {}. Skipping this server.".format(settings_file))
                console.error("Unable to find {}. Skipping this server.".format(settings_file))
                continue

            settings = ServerProps(settings_file)

            temp_server_dict = {
                'server_id': s.get('server_id'),
                'server_data_obj': s,
                'server_obj': Server(),
                'server_settings': settings.props
            }

            # setup the server, do the auto start and all that jazz
            temp_server_dict['server_obj'].do_server_setup(s)

            # add this temp object to the list of init servers
            self.servers_list.append(temp_server_dict)

            console.info("Loaded Server: ID {} | Name: {} | Autostart: {} | Delay: {} ".format(
                s['server_id'],
                s['server_name'],
                s['auto_start'],
                s['auto_start_delay']
            ))

    def get_server_obj(self, server_id):

        for s in self.servers_list:
            if int(s['server_id']) == int(server_id):
                return s['server_obj']

        logger.warning("Unable to find server object for server id {}".format(server_id))
        return False

    @staticmethod
    def list_defined_servers():
        servers = db_helper.get_all_defined_servers()
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
        logger.info("Found {} running server(s)".format(len(servers)))
        console.info("Found {} running server(s)".format(len(servers)))

        logger.info("Stopping All Servers")
        console.info("Stopping All Servers")

        for s in servers:
            logger.info("Stopping Server ID {} - {}".format(s['id'], s['name']))
            console.info("Stopping Server ID {} - {}".format(s['id'], s['name']))

            # get object
            svr_obj = self.get_server_obj(s['id'])
            running = svr_obj.check_running(True)

            # issue the stop command
            svr_obj.stop_threaded_server()

            # while it's running, we wait
            x = 0
            while running:
                logger.info("Server {} is still running - waiting 2s to see if it stops".format(s['name']))
                console.info("Server {} is still running - waiting 2s to see if it stops".format(s['name']))
                running = svr_obj.check_running()

                # let's keep track of how long this is going on...
                x = x + 1

                # if we have been waiting more than 120 seconds. let's just kill the pid
                if x >= 60:
                    logger.error("Server {} is taking way too long to stop. Killing this process".format(s['name']))
                    console.error("Server {} is taking way too long to stop. Killing this process".format(s['name']))

                    svr_obj.killpid(svr_obj.PID)
                    running = False

                # if we killed the server, let's clean up the object
                if not running:
                    svr_obj.cleanup_server_object()

                time.sleep(2)

            # let's wait 2 seconds to let everything flush out
            time.sleep(2)

        logger.info("All Servers Stopped")
        console.info("All Servers Stopped")

    def create_jar_server(self, server: str, version: str, name: str, min_mem: int, max_mem: int, port: int):
        server_id = helper.create_uuid()
        server_dir = os.path.join(helper.servers_dir, server_id)

        server_file = "{server}-{version}.jar".format(server=server, version=version)
        full_jar_path = os.path.join(server_dir, server_file)

        # make the dir - perhaps a UUID?
        helper.ensure_dir_exists(server_dir)

        try:
            # do a eula.txt
            with open(os.path.join(server_dir, "eula.txt"), 'w') as f:
                f.write("eula=true")
                f.close()

            # setup server.properties with the port
            with open(os.path.join(server_dir, "server.properties"), "w") as f:
                f.write("server-port={}".format(port))
                f.close()

        except Exception as e:
            logger.error("Unable to create required server files due to :{}".format(e))
            return False

        server_command = 'java -Xms{}G -Xmx{}G -jar {} nogui'.format(min_mem, max_mem, full_jar_path)
        server_log_file = "{}/logs/latest.log".format(server_dir)
        server_stop = "stop"

        # download the jar
        server_jar_obj.download_jar(server, version, full_jar_path, server_command, server_file)

        self.register_server(name, server_id, server_dir, server_command, server_file, server_log_file, server_stop)

    # todo - Do import server
    def import_server(self):
        print("todo")

    def register_server(self, name: str, server_id: str, server_dir: str, server_command: str, server_file: str,
                        server_log_file: str, server_stop: str):
        # put data in the db
        new_id = Servers.insert({
            Servers.server_name: name,
            Servers.server_uuid: server_id,
            Servers.path: server_dir,
            Servers.executable: server_file,
            Servers.execution_command: server_command,
            Servers.auto_start: False,
            Servers.auto_start_delay: 10,
            Servers.crash_detection: False,
            Servers.log_path: server_log_file,
            Servers.stop_command: server_stop
        }).execute()

        try:
            # place a file in the dir saying it's owned by crafty
            with open(os.path.join(server_dir, "crafty_managed.txt"), 'w') as f:
                f.write(
                    "The server is managed by Crafty Controller.\n Leave this directory/files alone please")
                f.close()

        except Exception as e:
            logger.error("Unable to create required server files due to :{}".format(e))
            return False

        # let's re-init all servers
        self.init_all_servers()

        return new_id


controller = Controller()
