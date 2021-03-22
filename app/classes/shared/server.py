import os
import sys
import re
import json
import time
import psutil
import pexpect
import datetime
import threading
import schedule
import logging.config


from app.classes.shared.helpers import helper
from app.classes.shared.console import console
from app.classes.shared.models import db_helper, Servers

logger = logging.getLogger(__name__)


try:
    import pexpect

except ModuleNotFoundError as e:
    logger.critical("Import Error: Unable to load {} module".format(e, e.name))
    console.critical("Import Error: Unable to load {} module".format(e, e.name))
    sys.exit(1)


class Server:

    def __init__(self):
        # holders for our process
        self.process = None
        self.line = False
        self.PID = None
        self.start_time = None
        self.server_command = None
        self.server_path = None
        self.server_thread = None
        self.settings = None
        self.updating = False
        self.server_id = None
        self.name = None
        self.is_crashed = False
        self.restart_count = 0
        self.crash_watcher_schedule = None

    def reload_server_settings(self):
        server_data = db_helper.get_server_data_by_id(self.server_id)
        self.settings = server_data

    def do_server_setup(self, server_data_obj):
        logger.info('Creating Server object: {} | Server Name: {} | Auto Start: {}'.format(
                                                                server_data_obj['server_id'],
                                                                server_data_obj['server_name'],
                                                                server_data_obj['auto_start']
                                                            ))
        self.server_id = server_data_obj['server_id']
        self.name = server_data_obj['server_name']
        self.settings = server_data_obj

        # build our server run command
        self.setup_server_run_command()

        if server_data_obj['auto_start']:
            delay = int(self.settings['auto_start_delay'])

            logger.info("Scheduling server {} to start in {} seconds".format(self.name, delay))
            console.info("Scheduling server {} to start in {} seconds".format(self.name, delay))

            schedule.every(delay).seconds.do(self.run_scheduled_server)

    def run_scheduled_server(self):
        console.info("Starting server ID: {} - {}".format(self.server_id, self.name))
        logger.info("Starting server {}".format(self.server_id, self.name))
        self.run_threaded_server()

        # remove the scheduled job since it's ran
        return schedule.CancelJob

    def run_threaded_server(self):
        # start the server
        self.server_thread = threading.Thread(target=self.start_server, daemon=True)
        self.server_thread.start()

    def setup_server_run_command(self):
        # configure the server
        server_exec_path = self.settings['executable']
        self.server_command = self.settings['execution_command']
        self.server_path = self.settings['path']

        # let's do some quick checking to make sure things actually exists
        full_path = os.path.join(self.server_path, server_exec_path)
        if not helper.check_file_exists(full_path):
            logger.critical("Server executable path: {} does not seem to exist".format(full_path))
            console.critical("Server executable path: {} does not seem to exist".format(full_path))
            helper.do_exit()

        if not helper.check_path_exists(self.server_path):
            logger.critical("Server path: {} does not seem to exits".format(self.server_path))
            console.critical("Server path: {} does not seem to exits".format(self.server_path))
            helper.do_exit()

        if not helper.check_writeable(self.server_path):
            logger.critical("Unable to write/access {}".format(self.server_path))
            console.warning("Unable to write/access {}".format(self.server_path))
            helper.do_exit()

    def start_server(self):
        from app.classes.minecraft.stats import stats

        # fail safe in case we try to start something already running
        if self.check_running():
            logger.error("Server is already running - Cancelling Startup")
            console.error("Server is already running - Cancelling Startup")
            return False

        logger.info("Launching Server {} with command {}".format(self.name, self.server_command))
        console.info("Launching Server {} with command {}".format(self.name, self.server_command))

        if os.name == "nt":
            logger.info("Windows Detected")
            self.server_command = self.server_command.replace('\\', '/')
        else:
            logger.info("Linux Detected")

        logger.info("Starting server in {p} with command: {c}".format(p=self.server_path, c=self.server_command))
        self.process = pexpect.spawn(self.server_command, cwd=self.server_path, timeout=None, encoding=None)
        self.is_crashed = False

        ts = time.time()
        self.start_time = str(datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'))

        if psutil.pid_exists(self.process.pid):
            self.PID = self.process.pid
            logger.info("Server {} running with PID {}".format(self.name, self.PID))
            console.info("Server {} running with PID {}".format(self.name, self.PID))
            self.is_crashed = False
            stats.record_stats()
        else:
            logger.warning("Server PID {} died right after starting - is this a server config issue?".format(self.PID))
            console.warning("Server PID {} died right after starting - is this a server config issue?".format(self.PID))

        if self.settings['crash_detection']:
            logger.info("Server {} has crash detection enabled - starting watcher task".format(self.name))
            console.info("Server {} has crash detection enabled - starting watcher task".format(self.name))

            self.crash_watcher_schedule = schedule.every(30).seconds.do(self.detect_crash).tag(self.name)

    def stop_threaded_server(self):
        self.stop_server()

        if self.server_thread:
            self.server_thread.join()

    def stop_server(self):
        from app.classes.minecraft.stats import stats
        if self.settings['stop_command']:
            self.send_command(self.settings['stop_command'])

            running = self.check_running()
            x = 0

            # caching the name and pid number
            server_name = self.name
            server_pid = self.PID

            while running:
                x = x+1
                logger.info("Server {} is still running - waiting 2s to see if it stops".format(server_name))
                console.info("Server {} is still running - waiting 2s to see if it stops".format(server_name))
                console.info("Server has {} seconds to respond before we force it down".format(int(60-(x*2))))
                running = self.check_running()
                time.sleep(2)

                # if we haven't closed in 60 seconds, let's just slam down on the PID
                if x >= 30:
                    logger.info("Server {} is still running - Forcing the process down".format(server_name))
                    console.info("Server {} is still running - Forcing the process down".format(server_name))
                    self.process.terminate(force=True)

            logger.info("Stopped Server {} with PID {}".format(server_name, server_pid))
            console.info("Stopped Server {} with PID {}".format(server_name, server_pid))

        else:
            self.process.terminate(force=True)

        # massive resetting of variables
        self.cleanup_server_object()

        stats.record_stats()

    def restart_threaded_server(self):

        # if not already running, let's just start
        if not self.check_running():
            self.run_threaded_server()
        else:
            self.stop_threaded_server()
            time.sleep(2)
            self.run_threaded_server()

    def cleanup_server_object(self):
        self.PID = None
        self.start_time = None
        self.restart_count = 0
        self.is_crashed = False
        self.updating = False
        self.process = None

    def check_running(self):
        running = False
        # if process is None, we never tried to start
        if self.PID is None:
            return running

        try:
            alive = self.process.isalive()
            if type(alive) is not bool:
                self.last_rc = alive
                running = False
            else:
                running = alive

        except Exception as e:
            logger.error("Unable to find if server PID exists: {}".format(self.PID), exc_info=True)
            pass

        return running

    def send_command(self, command):

        if not self.check_running() and command.lower() != 'start':
            logger.warning("Server not running, unable to send command \"{}\"".format(command))
            return False

        logger.debug("Sending command {} to server via pexpect".format(command))

        # send it
        self.process.send(command + '\n')

    def crash_detected(self, name):

        # clear the old scheduled watcher task
        self.remove_watcher_thread()

        # the server crashed, or isn't found - so let's reset things.
        logger.warning("The server {} seems to have vanished unexpectedly, did it crash?".format(name))

        if self.settings['crash_detection']:
            logger.warning("The server {} has crashed and will be restarted. Restarting server".format(name))
            console.warning("The server {} has crashed and will be restarted. Restarting server".format(name))
            self.run_threaded_server()
            return True
        else:
            logger.critical(
                "The server {} has crashed, crash detection is disabled and it will not be restarted".format(name))
            console.critical(
                "The server {} has crashed, crash detection is disabled and it will not be restarted".format(name))
            return False

    def killpid(self, pid):
        logger.info("Terminating PID {} and all child processes".format(pid))
        process = psutil.Process(pid)

        # for every sub process...
        for proc in process.children(recursive=True):
            # kill all the child processes - it sounds too wrong saying kill all the children (kevdagoat: lol!)
            logger.info("Sending SIGKILL to PID {}".format(proc.name))
            proc.kill()
        # kill the main process we are after
        logger.info('Sending SIGKILL to parent')
        process.kill()

    def get_start_time(self):
        if self.check_running():
            return self.start_time
        else:
            return False

    def detect_crash(self):

        logger.info("Detecting possible crash for server: {} ".format(self.name))

        running = self.check_running()

        # if all is okay, we just exit out
        if running:
            return

        # if we haven't tried to restart more 3 or more times
        if self.restart_count <= 3:

            # start the server if needed
            server_restarted = self.crash_detected(self.name)

            if server_restarted:
                # add to the restart count
                self.restart_count = self.restart_count + 1

        # we have tried to restart 4 times...
        elif self.restart_count == 4:
            logger.critical("Server {} has been restarted {} times. It has crashed, not restarting.".format(
                self.name, self.restart_count))

            console.critical("Server {} has been restarted {} times. It has crashed, not restarting.".format(
                self.name, self.restart_count))

            # set to 99 restart attempts so this elif is skipped next time. (no double logging)
            self.restart_count = 99
            self.is_crashed = True

            # cancel the watcher task
            self.remove_watcher_thread()

    def remove_watcher_thread(self):
        logger.info("Removing old crash detection watcher thread")
        console.info("Removing old crash detection watcher thread")
        schedule.clear(self.name)
