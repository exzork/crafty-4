import os
import time
import logging
import sys
import yaml

from app.classes.shared.helpers import helper
from app.classes.shared.console import console

from app.classes.shared.models import db_helper

from app.classes.minecraft.server import Server
from app.classes.minecraft.server_props import ServerProps

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


controller = Controller()
