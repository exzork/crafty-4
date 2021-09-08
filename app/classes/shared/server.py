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
import zipfile
from threading import Thread
import shutil
import zlib
import html


from app.classes.shared.helpers import helper
from app.classes.shared.console import console
from app.classes.models.servers import Servers, servers_helper
from app.classes.models.management import management_helper
from app.classes.web.websocket_helper import websocket_helper

logger = logging.getLogger(__name__)


try:
    import pexpect

except ModuleNotFoundError as e:
    logger.critical("Import Error: Unable to load {} module".format(e.name), exc_info=True)
    console.critical("Import Error: Unable to load {} module".format(e.name))
    sys.exit(1)


class ServerOutBuf:
    lines = {}

    def __init__(self, p, server_id):
        self.p = p
        self.server_id = str(server_id)
        # Buffers text for virtual_terminal_lines config number of lines
        self.max_lines = helper.get_setting('virtual_terminal_lines')
        self.line_buffer = ''
        ServerOutBuf.lines[self.server_id] = []

    def check(self):
        while self.p.isalive():
            char = self.p.read(1)
            if char == os.linesep:
                ServerOutBuf.lines[self.server_id].append(self.line_buffer)
                self.new_line_handler(self.line_buffer)
                self.line_buffer = ''
                # Limit list length to self.max_lines:
                if len(ServerOutBuf.lines[self.server_id]) > self.max_lines:
                    ServerOutBuf.lines[self.server_id].pop(0)
            else:
                self.line_buffer += char

    def new_line_handler(self, new_line):
        new_line = re.sub('(\033\\[(0;)?[0-9]*[A-z]?(;[0-9])?m?)|(> )', '', new_line)
        new_line = re.sub('[A-z]{2}\b\b', '', new_line)
        highlighted = helper.log_colors(html.escape(new_line))

        logger.debug('Broadcasting new virtual terminal line')

        # TODO: Do not send data to clients who do not have permission to view this server's console
        websocket_helper.broadcast_page_params(
            '/panel/server_detail',
            {
                'id': self.server_id
            },
            'vterm_new_line',
            {
                'line': highlighted + '<br />'
            }
        )


class Server:

    def __init__(self, stats):
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
        self.jar_update_url = None
        self.name = None
        self.is_crashed = False
        self.restart_count = 0
        self.crash_watcher_schedule = None
        self.stats = stats
        self.backup_thread = threading.Thread(target=self.a_backup_server, daemon=True, name="backup")
        self.is_backingup = False

    def reload_server_settings(self):
        server_data = servers_helper.get_server_data_by_id(self.server_id)
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
        self.server_thread = threading.Thread(target=self.start_server, daemon=True, name='{}_server_thread'.format(self.server_id))
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

        if not helper.check_path_exists(self.server_path):
            logger.critical("Server path: {} does not seem to exits".format(self.server_path))
            console.critical("Server path: {} does not seem to exits".format(self.server_path))
            helper.do_exit()

        if not helper.check_writeable(self.server_path):
            logger.critical("Unable to write/access {}".format(self.server_path))
            console.warning("Unable to write/access {}".format(self.server_path))
            helper.do_exit()

    def start_server(self):

        logger.info("Start command detected. Reloading settings from DB for server {}".format(self.name))
        self.setup_server_run_command()
        # fail safe in case we try to start something already running
        if self.check_running():
            logger.error("Server is already running - Cancelling Startup")
            console.error("Server is already running - Cancelling Startup")
            return False
        if self.check_update():
            logger.error("Server is updating. Terminating startup.")
            return False

        logger.info("Launching Server {} with command {}".format(self.name, self.server_command))
        console.info("Launching Server {} with command {}".format(self.name, self.server_command))

        if os.name == "nt":
            logger.info("Windows Detected")
            self.server_command = self.server_command.replace('\\', '/')
        else:
            logger.info("Linux Detected")

        logger.info("Starting server in {p} with command: {c}".format(p=self.server_path, c=self.server_command))
        try:
            self.process = pexpect.spawn(self.server_command, cwd=self.server_path, timeout=None, encoding=None)
        except Exception as ex:
            msg = "Server {} failed to start with error code: {}".format(self.name, ex)
            logger.error(msg)
            websocket_helper.broadcast('send_start_error', {
                'error': msg
            })
            return False
        websocket_helper.broadcast('send_start_reload', {
        })

        self.process = pexpect.spawn(self.server_command, cwd=self.server_path, timeout=None, encoding='utf-8')
        out_buf = ServerOutBuf(self.process, self.server_id)

        logger.debug('Starting virtual terminal listener for server {}'.format(self.name))
        threading.Thread(target=out_buf.check, daemon=True, name='{}_virtual_terminal'.format(self.server_id)).start()

        self.is_crashed = False

        self.start_time = str(datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))

        if psutil.pid_exists(self.process.pid):
            self.PID = self.process.pid
            logger.info("Server {} running with PID {}".format(self.name, self.PID))
            console.info("Server {} running with PID {}".format(self.name, self.PID))
            self.is_crashed = False
            self.stats.record_stats()
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

        self.stats.record_stats()

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

    def is_backup_running(self):
        if self.is_backingup:
            return True
        else:
            return False

    def backup_server(self):
        backup_thread = threading.Thread(target=self.a_backup_server, daemon=True, name="backup")
        logger.info("Starting Backup Thread for server {}.".format(self.settings['server_name']))
        #checks if the backup thread is currently alive for this server
        if not self.is_backingup:
            try:
                backup_thread.start()
            except Exception as ex:
                logger.error("Failed to start backup: {}".format(ex))
                return False
        else:
            logger.error("Backup is already being processed for server {}. Canceling backup request".format(self.settings['server_name']))
            return False
        logger.info("Backup Thread started for server {}.".format(self.settings['server_name']))

    def a_backup_server(self):
        logger.info("Starting server {} (ID {}) backup".format(self.name, self.server_id))
        self.is_backingup = True
        conf = management_helper.get_backup_config(self.server_id)
        try:
            backup_filename = "{}/{}".format(self.settings['backup_path'], datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
            logger.info("Creating backup of server '{}' (ID#{}) at '{}'".format(self.settings['server_name'], self.server_id, backup_filename))
            shutil.make_archive(backup_filename, 'zip', self.server_path)
            while len(self.list_backups()) > conf["max_backups"] and conf["max_backups"] > 0:
                backup_list = self.list_backups()
                oldfile = backup_list[0]
                oldfile_path = "{}/{}".format(conf['backup_path'], oldfile['path'])
                logger.info("Removing old backup '{}'".format(oldfile['path']))
                os.remove(oldfile_path)
            self.is_backingup = False
            logger.info("Backup of server: {} completed".format(self.name))
            return
        except:
            logger.exception("Failed to create backup of server {} (ID {})".format(self.name, self.server_id))
            self.is_backingup = False
            return

    def list_backups(self):
        conf = management_helper.get_backup_config(self.server_id)
        if helper.check_path_exists(self.settings['backup_path']):
            files = helper.get_human_readable_files_sizes(helper.list_dir_by_date(self.settings['backup_path']))
            return [{"path": os.path.relpath(f['path'], start=conf['backup_path']), "size": f["size"]} for f in files]
        else:
            return []

    def jar_update(self):
        servers_helper.set_update(self.server_id, True)
        update_thread = threading.Thread(target=self.a_jar_update, daemon=True, name="exe_update")
        update_thread.start()

    def check_update(self):
        server_stats = servers_helper.get_server_stats_by_id(self.server_id)
        if server_stats['updating']:
            return True
        else:
            return False

    def a_jar_update(self):
        error = False
        wasStarted = "-1"
        self.backup_server()
        #checks if server is running. Calls shutdown if it is running.
        if self.check_running():
            wasStarted = True
            logger.info("Server with PID {} is running. Sending shutdown command".format(self.PID))
            self.stop_threaded_server()
        else:
            wasStarted = False
        if len(websocket_helper.clients) > 0:
            # There are clients
            self.check_update()
            message = '<a data-id="'+str(self.server_id)+'" class=""> UPDATING...</i></a>'
            websocket_helper.broadcast('update_button_status', {
                'isUpdating': self.check_update(),
                'server_id': self.server_id,
                'wasRunning': wasStarted,
                'string': message
            })
        backup_dir = os.path.join(self.settings['path'], 'crafty_executable_backups')
        #checks if backup directory already exists
        if os.path.isdir(backup_dir):
            backup_executable = os.path.join(backup_dir, 'old_server.jar')
        else:
            logger.info("Executable backup directory not found for Server: {}. Creating one.".format(self.name))
            os.mkdir(backup_dir)
            backup_executable = os.path.join(backup_dir, 'old_server.jar')

            if os.path.isfile(backup_executable):
                #removes old backup
                logger.info("Old backup found for server: {}. Removing...".format(self.name))
                os.remove(backup_executable)
                logger.info("Old backup removed for server: {}.".format(self.name))
            else:
                logger.info("No old backups found for server: {}".format(self.name))

        current_executable = os.path.join(self.settings['path'], self.settings['executable'])

        #copies to backup dir
        helper.copy_files(current_executable, backup_executable)

    #boolean returns true for false for success
        downloaded = helper.download_file(self.settings['executable_update_url'], current_executable)

        while servers_helper.get_server_stats_by_id(self.server_id)['updating']:
            if downloaded and not self.is_backingup:
                print("Backup Status: " + str(self.is_backingup))
                logger.info("Executable updated successfully. Starting Server")

                servers_helper.set_update(self.server_id, False)
                if len(websocket_helper.clients) > 0:
                    # There are clients
                    self.check_update()
                    websocket_helper.broadcast('notification', "Executable update finished for " + self.name)
                    time.sleep(3)
                    websocket_helper.broadcast('update_button_status', {
                        'isUpdating': self.check_update(),
                        'server_id': self.server_id,
                        'wasRunning': wasStarted
                    })
                websocket_helper.broadcast('notification', "Executable update finished for "+self.name)

                management_helper.add_to_audit_log_raw('Alert', '-1', self.server_id, "Executable update finished for "+self.name, self.settings['server_ip'])
                if wasStarted:
                    self.start_server()
            elif not downloaded and not self.is_backingup:
                time.sleep(5)
                servers_helper.set_update(self.server_id, False)
                websocket_helper.broadcast('notification',
                                           "Executable update failed for " + self.name + ". Check log file for details.")
                logger.error("Executable download failed.")
            pass
