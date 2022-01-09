import os
import sys
import re
import json
import time
import datetime
import threading
import logging.config
import zipfile
from threading import Thread
import shutil
import subprocess
import zlib
import html


from app.classes.shared.helpers import helper
from app.classes.shared.console import console
from app.classes.models.servers import Servers, helper_servers, servers_helper
from app.classes.models.management import management_helper
from app.classes.web.websocket_helper import websocket_helper
from app.classes.shared.translation import translation
from app.classes.models.users import users_helper

logger = logging.getLogger(__name__)


try:
    import psutil
    #import pexpect
    import schedule

except ModuleNotFoundError as e:
    logger.critical("Import Error: Unable to load {} module".format(e.name), exc_info=True)
    console.critical("Import Error: Unable to load {} module".format(e.name))
    sys.exit(1)


class ServerOutBuf:
    lines = {}

    def __init__(self, proc, server_id):
        self.proc = proc
        self.server_id = str(server_id)
        # Buffers text for virtual_terminal_lines config number of lines
        self.max_lines = helper.get_setting('virtual_terminal_lines')
        self.line_buffer = ''
        ServerOutBuf.lines[self.server_id] = []
        self.lsi = 0

    def process_byte(self, char):
        if char == os.linesep[self.lsi]:
            self.lsi += 1
        else:
            self.lsi = 0
            self.line_buffer += char

        if self.lsi >= len(os.linesep):
            self.lsi = 0
            ServerOutBuf.lines[self.server_id].append(self.line_buffer)

            self.new_line_handler(self.line_buffer)
            self.line_buffer = ''
            # Limit list length to self.max_lines:
            if len(ServerOutBuf.lines[self.server_id]) > self.max_lines:
                ServerOutBuf.lines[self.server_id].pop(0)

    def check(self):
        while True:
            if self.proc.poll() is None:
                char = self.proc.stdout.read(1).decode('utf-8', 'ignore')
                # TODO: we may want to benchmark reading in blocks and userspace processing it later, reads are kind of expensive as a syscall
                self.process_byte(char)
            else:
                flush = self.proc.stdout.read().decode('utf-8', 'ignore')
                for char in flush:
                    self.process_byte(char)
                break

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
        self.backup_thread = threading.Thread(target=self.a_backup_server, daemon=True, name=f"backup_{self.name}")
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
        self.run_threaded_server(None)

        # remove the scheduled job since it's ran
        return schedule.CancelJob

    def run_threaded_server(self, user_id):
        # start the server
        self.server_thread = threading.Thread(target=self.start_server, daemon=True, args=(user_id,), name='{}_server_thread'.format(self.server_id))
        self.server_thread.start()

    def setup_server_run_command(self):
        # configure the server
        server_exec_path = helper.get_os_understandable_path(self.settings['executable'])
        self.server_command = helper.cmdparse(self.settings['execution_command'])
        self.server_path = helper.get_os_understandable_path(self.settings['path'])

        # let's do some quick checking to make sure things actually exists
        full_path = os.path.join(self.server_path, server_exec_path)
        if not helper.check_file_exists(full_path):
            logger.critical("Server executable path: {} does not seem to exist".format(full_path))
            console.critical("Server executable path: {} does not seem to exist".format(full_path))

        if not helper.check_path_exists(self.server_path):
            logger.critical("Server path: {} does not seem to exits".format(self.server_path))
            console.critical("Server path: {} does not seem to exits".format(self.server_path))

        if not helper.check_writeable(self.server_path):
            logger.critical("Unable to write/access {}".format(self.server_path))
            console.warning("Unable to write/access {}".format(self.server_path))

    def start_server(self, user_id):
        if not user_id:
            user_lang = helper.get_setting('language')
        else:
            user_lang = users_helper.get_user_lang_by_id(user_id)

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

    #Checks for eula. Creates one if none detected.
    #If EULA is detected and not set to one of these true vaiants we offer to set it true.
        if helper.check_file_exists(os.path.join(self.settings['path'], 'eula.txt')):
            f = open(os.path.join(self.settings['path'], 'eula.txt'), 'r')
            line = f.readline().lower()
            if line == 'eula=true':
                e_flag = True

            elif line == 'eula = true':
                e_flag = True

            elif line == 'eula= true':
                e_flag = True

            elif line == 'eula =true':
                e_flag = True

            else:
                e_flag = False
        else:
            e_flag = False

        if e_flag == False:
            if user_id:
                websocket_helper.broadcast_user(user_id, 'send_eula_bootbox', {
                    'id': self.server_id
                    })
            else:
                logger.error("Autostart failed due to EULA being false. Agree not sent due to auto start.")
                servers_helper.set_waiting_start(self.server_id, False)
                return False
            return False
        f.close()
        if helper.is_os_windows():
            logger.info("Windows Detected")
            creationflags=subprocess.CREATE_NEW_CONSOLE
        else:
            logger.info("Unix Detected")
            creationflags=None

        logger.info("Starting server in {p} with command: {c}".format(p=self.server_path, c=self.server_command))

        #Sets waiting start to false since server is now starting.
        servers_helper.set_waiting_start(self.server_id, False)
        
        try:
            self.process = subprocess.Popen(self.server_command, cwd=self.server_path, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except Exception as ex:
            #Checks for java on initial fail
            if os.system("java -version") == 32512:
                msg = "Server {} failed to start with error code: {}".format(self.name, "Java not found. Please install Java then try again.")
                if user_id:
                    websocket_helper.broadcast_user(user_id, 'send_start_error',{
                    'error': translation.translate('error', 'noJava', user_lang).format(self.name)
                })
                return False
            else:
                msg = "Server {} failed to start with error code: {}".format(self.name, ex)
            logger.error(msg)
            if user_id:
                websocket_helper.broadcast_user(user_id, 'send_start_error',{
                    'error': translation.translate('error', 'start-error', user_lang).format(self.name, ex)
                })
            return False

        out_buf = ServerOutBuf(self.process, self.server_id)

        logger.debug('Starting virtual terminal listener for server {}'.format(self.name))
        threading.Thread(target=out_buf.check, daemon=True, name='{}_virtual_terminal'.format(self.server_id)).start()

        self.is_crashed = False

        self.start_time = str(datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))

        if self.process.poll() is None:
            logger.info("Server {} running with PID {}".format(self.name, self.process.pid))
            console.info("Server {} running with PID {}".format(self.name, self.process.pid))
            self.is_crashed = False
            self.stats.record_stats()
            check_internet_thread = threading.Thread(target=self.check_internet_thread, daemon=True, args=(user_id, user_lang, ), name="{self.name}_Internet")
            check_internet_thread.start()
            #Checks if this is the servers first run.
            if servers_helper.get_server_stats_by_id(self.server_id)['first_run']:
                loc_server_port = servers_helper.get_server_stats_by_id(self.server_id)['server_port']
                #Sends port reminder message.
                websocket_helper.broadcast_user(user_id, 'send_start_error', {
                    'error': translation.translate('error', 'portReminder', user_lang).format(self.name, loc_server_port)
                })
                servers_helper.set_first_run(self.server_id)
            else:
                websocket_helper.broadcast_user(user_id, 'send_start_reload', {
                })
        else:
            logger.warning("Server PID {} died right after starting - is this a server config issue?".format(self.process.pid))
            console.warning("Server PID {} died right after starting - is this a server config issue?".format(self.process.pid))

        if self.settings['crash_detection']:
            logger.info("Server {} has crash detection enabled - starting watcher task".format(self.name))
            console.info("Server {} has crash detection enabled - starting watcher task".format(self.name))

            self.crash_watcher_schedule = schedule.every(30).seconds.do(self.detect_crash).tag(self.name)
            
    def check_internet_thread(self, user_id, user_lang):
        if user_id:
            if not helper.check_internet():
                websocket_helper.broadcast_user(user_id, 'send_start_error', {
                    'error': translation.translate('error', 'internet', user_lang)
                })
        return

    def stop_threaded_server(self):
        self.stop_server()

        if self.server_thread:
            self.server_thread.join()

    def stop_server(self):
        if self.settings['stop_command']:
            self.send_command(self.settings['stop_command'])
        else:
            #windows will need to be handled separately for Ctrl+C
            self.process.terminate()
        running = self.check_running()
        if not running:
            logger.info("Can't stop server {} if it's not running".format(self.name))
            console.info("Can't stop server {} if it's not running".format(self.name))
            return
        x = 0

        # caching the name and pid number
        server_name = self.name
        server_pid = self.process.pid

        while running:
            x = x+1
            logstr = "Server {} is still running - waiting 2s to see if it stops ({} seconds until force close)".format(server_name, int(60-(x*2)))
            logger.info(logstr)
            console.info(logstr)
            running = self.check_running()
            time.sleep(2)

            # if we haven't closed in 60 seconds, let's just slam down on the PID
            if x >= 30:
                logger.info("Server {} is still running - Forcing the process down".format(server_name))
                console.info("Server {} is still running - Forcing the process down".format(server_name))
                self.kill()

        logger.info("Stopped Server {} with PID {}".format(server_name, server_pid))
        console.info("Stopped Server {} with PID {}".format(server_name, server_pid))

        # massive resetting of variables
        self.cleanup_server_object()

        self.stats.record_stats()

    def restart_threaded_server(self, user_id):
        # if not already running, let's just start
        if not self.check_running():
            self.run_threaded_server(user_id)
        else:
            self.stop_threaded_server()
            time.sleep(2)
            self.run_threaded_server(user_id)

    def cleanup_server_object(self):
        self.start_time = None
        self.restart_count = 0
        self.is_crashed = False
        self.updating = False
        self.process = None

    def check_running(self):
        # if process is None, we never tried to start
        if self.process is None:
            return False
        poll = self.process.poll()
        if poll is None:
            return True
        else:
            self.last_rc = poll
            return False

    def send_command(self, command):
        console.info("COMMAND TIME: {}".format(command))
        if not self.check_running() and command.lower() != 'start':
            logger.warning("Server not running, unable to send command \"{}\"".format(command))
            return False

        logger.debug("Sending command {} to server".format(command))

        # send it
        self.process.stdin.write("{}\n".format(command).encode('utf-8'))
        self.process.stdin.flush()

    def crash_detected(self, name):

        # clear the old scheduled watcher task
        self.remove_watcher_thread()

        # the server crashed, or isn't found - so let's reset things.
        logger.warning("The server {} seems to have vanished unexpectedly, did it crash?".format(name))

        if self.settings['crash_detection']:
            logger.warning("The server {} has crashed and will be restarted. Restarting server".format(name))
            console.warning("The server {} has crashed and will be restarted. Restarting server".format(name))
            self.run_threaded_server(None)
            return True
        else:
            logger.critical(
                "The server {} has crashed, crash detection is disabled and it will not be restarted".format(name))
            console.critical(
                "The server {} has crashed, crash detection is disabled and it will not be restarted".format(name))
            return False

    def kill(self):
        logger.info("Terminating server {} and all child processes".format(self.server_id))
        process = psutil.Process(self.process.pid)

        # for every sub process...
        for proc in process.children(recursive=True):
            # kill all the child processes - it sounds too wrong saying kill all the children (kevdagoat: lol!)
            logger.info("Sending SIGKILL to server {}".format(proc.name))
            proc.kill()
        # kill the main process we are after
        logger.info('Sending SIGKILL to parent')
        self.process.kill()

    def get_start_time(self):
        if self.check_running():
            return self.start_time
        else:
            return False

    def get_pid(self):
        if self.process is not None:
            return self.process.pid
        else:
            return None

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

    def agree_eula(self, user_id):
        file = os.path.join(self.server_path, 'eula.txt')
        f = open(file, 'w')
        f.write('eula=true')
        f.close
        self.run_threaded_server(user_id)

    def is_backup_running(self):
        if self.is_backingup:
            return True
        else:
            return False

    def backup_server(self):
        backup_thread = threading.Thread(target=self.a_backup_server, daemon=True, name=f"backup_{self.name}")
        logger.info("Starting Backup Thread for server {}.".format(self.settings['server_name']))
        if self.server_path == None:
            self.server_path = helper.get_os_understandable_path(self.settings['path'])
            logger.info("Backup Thread - Local server path not defined. Setting local server path variable.")
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
            shutil.make_archive(helper.get_os_understandable_path(backup_filename), 'zip', self.server_path)
            while len(self.list_backups()) > conf["max_backups"] and conf["max_backups"] > 0:
                backup_list = self.list_backups()
                oldfile = backup_list[0]
                oldfile_path = "{}/{}".format(conf['backup_path'], oldfile['path'])
                logger.info("Removing old backup '{}'".format(oldfile['path']))
                os.remove(helper.get_os_understandable_path(oldfile_path))
            self.is_backingup = False
            logger.info("Backup of server: {} completed".format(self.name))
            return
        except:
            logger.exception("Failed to create backup of server {} (ID {})".format(self.name, self.server_id))
            self.is_backingup = False
            return

    def list_backups(self):
        if self.settings['backup_path']:
            if helper.check_path_exists(helper.get_os_understandable_path(self.settings['backup_path'])):
                files = helper.get_human_readable_files_sizes(helper.list_dir_by_date(helper.get_os_understandable_path(self.settings['backup_path'])))
                return [{"path": os.path.relpath(f['path'], start=helper.get_os_understandable_path(self.settings['backup_path'])), "size": f["size"]} for f in files]
            else:
                return []
        else:
            logger.info("Error putting backup file list for server with ID: {}".format(self.server_id))
            return[]

    def jar_update(self):
        servers_helper.set_update(self.server_id, True)
        update_thread = threading.Thread(target=self.a_jar_update, daemon=True, name=f"exe_update_{self.name}")
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
            logger.info("Server with PID {} is running. Sending shutdown command".format(self.process.pid))
            self.stop_threaded_server()
        else:
            wasStarted = False
        if len(websocket_helper.clients) > 0:
            # There are clients
            self.check_update()
            message = '<a data-id="'+str(self.server_id)+'" class=""> UPDATING...</i></a>'
            websocket_helper.broadcast_page('/panel/server_detail', 'update_button_status', {
                'isUpdating': self.check_update(),
                'server_id': self.server_id,
                'wasRunning': wasStarted,
                'string': message
            })
            websocket_helper.broadcast_page('/panel/dashboard', 'send_start_reload', {
            })
        backup_dir = os.path.join(helper.get_os_understandable_path(self.settings['path']), 'crafty_executable_backups')
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

        current_executable = os.path.join(helper.get_os_understandable_path(self.settings['path']), self.settings['executable'])

        #copies to backup dir
        helper.copy_files(current_executable, backup_executable)

    #boolean returns true for false for success
        downloaded = helper.download_file(self.settings['executable_update_url'], current_executable)

        while servers_helper.get_server_stats_by_id(self.server_id)['updating']:
            if downloaded and not self.is_backingup:
                logger.info("Executable updated successfully. Starting Server")

                servers_helper.set_update(self.server_id, False)
                if len(websocket_helper.clients) > 0:
                    # There are clients
                    self.check_update()
                    websocket_helper.broadcast('notification', "Executable update finished for " + self.name)
                    time.sleep(3)
                    websocket_helper.broadcast_page('/panel/server_detail', 'update_button_status', {
                        'isUpdating': self.check_update(),
                        'server_id': self.server_id,
                        'wasRunning': wasStarted
                    })
                    websocket_helper.broadcast_page('/panel/dashboard', 'send_start_reload', {
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
