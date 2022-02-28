import os
import sys
import re
import time
import datetime
import threading
import logging.config
import shutil
import subprocess
import html
import tempfile
from apscheduler.schedulers.background import BackgroundScheduler
#TZLocal is set as a hidden import on win pipeline
from tzlocal import get_localzone

from app.classes.models.servers import servers_helper
from app.classes.models.management import management_helper
from app.classes.models.users import users_helper
from app.classes.models.server_permissions import server_permissions

from app.classes.shared.helpers import helper
from app.classes.shared.console import console
from app.classes.shared.translation import translation

from app.classes.web.websocket_helper import websocket_helper

logger = logging.getLogger(__name__)

try:
    import psutil

except ModuleNotFoundError as e:
    logger.critical(f"Import Error: Unable to load {e.name} module", exc_info=True)
    console.critical(f"Import Error: Unable to load {e.name} module")
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
        new_line = re.sub('(\033\\[(0;)?[0-9]*[A-z]?(;[0-9])?m?)', ' ', new_line)
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
        self.stats = stats
        tz = get_localzone()
        self.server_scheduler = BackgroundScheduler(timezone=str(tz))
        self.server_scheduler.start()
        self.backup_thread = threading.Thread(target=self.a_backup_server, daemon=True, name=f"backup_{self.name}")
        self.is_backingup = False
        #Reset crash and update at initialization
        servers_helper.server_crash_reset(self.server_id)
        servers_helper.set_update(self.server_id, False)

    def reload_server_settings(self):
        server_data = servers_helper.get_server_data_by_id(self.server_id)
        self.settings = server_data

    def do_server_setup(self, server_data_obj):
        serverId = server_data_obj['server_id']
        serverName = server_data_obj['server_name']
        autoStart = server_data_obj['auto_start']

        logger.info(f'Creating Server object: {serverId} | Server Name: {serverName} | Auto Start: {autoStart}')
        self.server_id = serverId
        self.name = serverName
        self.settings = server_data_obj

        # build our server run command

        if server_data_obj['auto_start']:
            delay = int(self.settings['auto_start_delay'])

            logger.info(f"Scheduling server {self.name} to start in {delay} seconds")
            console.info(f"Scheduling server {self.name} to start in {delay} seconds")

            self.server_scheduler.add_job(self.run_scheduled_server, 'interval', seconds=delay, id=str(self.server_id))

    def run_scheduled_server(self):
        console.info(f"Starting server ID: {self.server_id} - {self.name}")
        logger.info(f"Starting server ID: {self.server_id} - {self.name}")
        #Sets waiting start to false since we're attempting to start the server.
        servers_helper.set_waiting_start(self.server_id, False)
        self.run_threaded_server(None)

        # remove the scheduled job since it's ran
        return self.server_scheduler.remove_job(str(self.server_id))

    def run_threaded_server(self, user_id):
        # start the server
        self.server_thread = threading.Thread(target=self.start_server, daemon=True, args=(user_id,), name=f'{self.server_id}_server_thread')
        self.server_thread.start()

    def setup_server_run_command(self):
        # configure the server
        server_exec_path = helper.get_os_understandable_path(self.settings['executable'])
        self.server_command = helper.cmdparse(self.settings['execution_command'])
        self.server_path = helper.get_os_understandable_path(self.settings['path'])

        # let's do some quick checking to make sure things actually exists
        full_path = os.path.join(self.server_path, server_exec_path)
        if not helper.check_file_exists(full_path):
            logger.critical(f"Server executable path: {full_path} does not seem to exist")
            console.critical(f"Server executable path: {full_path} does not seem to exist")

        if not helper.check_path_exists(self.server_path):
            logger.critical(f"Server path: {self.server_path} does not seem to exits")
            console.critical(f"Server path: {self.server_path} does not seem to exits")

        if not helper.check_writeable(self.server_path):
            logger.critical(f"Unable to write/access {self.server_path}")
            console.warning(f"Unable to write/access {self.server_path}")

    def start_server(self, user_id):
        if not user_id:
            user_lang = helper.get_setting('language')
        else:
            user_lang = users_helper.get_user_lang_by_id(user_id)

        logger.info(f"Start command detected. Reloading settings from DB for server {self.name}")
        self.setup_server_run_command()
        # fail safe in case we try to start something already running
        if self.check_running():
            logger.error("Server is already running - Cancelling Startup")
            console.error("Server is already running - Cancelling Startup")
            return False
        if self.check_update():
            logger.error("Server is updating. Terminating startup.")
            return False

        logger.info(f"Launching Server {self.name} with command {self.server_command}")
        console.info(f"Launching Server {self.name} with command {self.server_command}")

        #Checks for eula. Creates one if none detected.
        #If EULA is detected and not set to one of these true vaiants we offer to set it true.
        if helper.check_file_exists(os.path.join(self.settings['path'], 'eula.txt')):
            f = open(os.path.join(self.settings['path'], 'eula.txt'), 'r', encoding='utf-8')
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

        if not e_flag:
            if user_id:
                websocket_helper.broadcast_user(user_id, 'send_eula_bootbox', {
                    'id': self.server_id
                    })
            else:
                logger.error("Autostart failed due to EULA being false. Agree not sent due to auto start.")
                return False
            return False
        f.close()
        if helper.is_os_windows():
            logger.info("Windows Detected")
        else:
            logger.info("Unix Detected")

        logger.info(f"Starting server in {self.server_path} with command: {self.server_command}")

        if not helper.is_os_windows() and servers_helper.get_server_type_by_id(self.server_id) == "minecraft-bedrock":
            logger.info(f"Bedrock and Unix detected for server {self.name}. Switching to appropriate execution string")
            my_env = os.environ
            my_env["LD_LIBRARY_PATH"] = self.server_path
            try:
                self.process = subprocess.Popen(
                    self.server_command, cwd=self.server_path, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=my_env)
            except Exception as ex:
                logger.error(f"Server {self.name} failed to start with error code: {ex}")
                if user_id:
                    websocket_helper.broadcast_user(user_id, 'send_start_error',{
                        'error': translation.translate('error', 'start-error', user_lang).format(self.name, ex)
                    })
                return False

        else:
            try:
                self.process = subprocess.Popen(
                    self.server_command, cwd=self.server_path, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            except Exception as ex:
                #Checks for java on initial fail
                if os.system("java -version") == 32512:
                    if user_id:
                        websocket_helper.broadcast_user(user_id, 'send_start_error',{
                        'error': translation.translate('error', 'noJava', user_lang).format(self.name)
                    })
                    return False
                else:
                    logger.error(f"Server {self.name} failed to start with error code: {ex}")
                if user_id:
                    websocket_helper.broadcast_user(user_id, 'send_start_error',{
                        'error': translation.translate('error', 'start-error', user_lang).format(self.name, ex)
                    })
                return False

        out_buf = ServerOutBuf(self.process, self.server_id)

        logger.debug(f'Starting virtual terminal listener for server {self.name}')
        threading.Thread(target=out_buf.check, daemon=True, name=f'{self.server_id}_virtual_terminal').start()

        self.is_crashed = False
        servers_helper.server_crash_reset(self.server_id)

        self.start_time = str(datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))

        if self.process.poll() is None:
            logger.info(f"Server {self.name} running with PID {self.process.pid}")
            console.info(f"Server {self.name} running with PID {self.process.pid}")
            self.is_crashed = False
            servers_helper.server_crash_reset(self.server_id)
            self.stats.record_stats()
            check_internet_thread = threading.Thread(
                target=self.check_internet_thread, daemon=True, args=(user_id, user_lang, ), name=f"{self.name}_Internet")
            check_internet_thread.start()
            #Checks if this is the servers first run.
            if servers_helper.get_first_run(self.server_id):
                servers_helper.set_first_run(self.server_id)
                loc_server_port = servers_helper.get_server_stats_by_id(self.server_id)['server_port']
                #Sends port reminder message.
                websocket_helper.broadcast_user(user_id, 'send_start_error', {
                    'error': translation.translate('error', 'portReminder', user_lang).format(self.name, loc_server_port)
                })
                server_users = server_permissions.get_server_user_list(self.server_id)
                for user in server_users:
                    if user != user_id:
                        websocket_helper.broadcast_user(user, 'send_start_reload', {
                })
            else:
                server_users = server_permissions.get_server_user_list(self.server_id)
                for user in server_users:
                    websocket_helper.broadcast_user(user, 'send_start_reload', {
                })
        else:
            logger.warning(f"Server PID {self.process.pid} died right after starting - is this a server config issue?")
            console.warning(f"Server PID {self.process.pid} died right after starting - is this a server config issue?")

        if self.settings['crash_detection']:
            logger.info(f"Server {self.name} has crash detection enabled - starting watcher task")
            console.info(f"Server {self.name} has crash detection enabled - starting watcher task")

            self.server_scheduler.add_job(self.detect_crash, 'interval', seconds=30, id=f"c_{self.server_id}")

    def check_internet_thread(self, user_id, user_lang):
        if user_id:
            if not helper.check_internet():
                websocket_helper.broadcast_user(user_id, 'send_start_error', {
                    'error': translation.translate('error', 'internet', user_lang)
                })

    def stop_crash_detection(self):
        #This is only used if the crash detection settings change while the server is running.
        if self.check_running():
            logger.info(f"Detected crash detection shut off for server {self.name}")
            try:
                self.server_scheduler.remove_job('c_' + str(self.server_id))
            except:
                logger.error(f"Removing crash watcher for server {self.name} failed. Assuming it was never started.")

    def start_crash_detection(self):
        #This is only used if the crash detection settings change while the server is running.
        if self.check_running():
            logger.info(f"Server {self.name} has crash detection enabled - starting watcher task")
            console.info(f"Server {self.name} has crash detection enabled - starting watcher task")
            self.server_scheduler.add_job(self.detect_crash, 'interval', seconds=30, id=f"c_{self.server_id}")

    def stop_threaded_server(self):
        self.stop_server()

        if self.server_thread:
            self.server_thread.join()

    def stop_server(self):
        if self.settings['stop_command']:
            self.send_command(self.settings['stop_command'])
            if self.settings['crash_detection']:
                #remove crash detection watcher
                logger.info(f"Removing crash watcher for server {self.name}")
                try:
                    self.server_scheduler.remove_job('c_' + str(self.server_id))
                except:
                    logger.error(f"Removing crash watcher for server {self.name} failed. Assuming it was never started.")
        else:
            #windows will need to be handled separately for Ctrl+C
            self.process.terminate()
        running = self.check_running()
        if not running:
            logger.info(f"Can't stop server {self.name} if it's not running")
            console.info(f"Can't stop server {self.name} if it's not running")
            return
        x = 0

        # caching the name and pid number
        server_name = self.name
        server_pid = self.process.pid


        while running:
            x = x+1
            logstr = f"Server {server_name} is still running - waiting 2s to see if it stops ({int(60-(x*2))} seconds until force close)"
            logger.info(logstr)
            console.info(logstr)
            running = self.check_running()
            time.sleep(2)

            # if we haven't closed in 60 seconds, let's just slam down on the PID
            if x >= 30:
                logger.info(f"Server {server_name} is still running - Forcing the process down")
                console.info(f"Server {server_name} is still running - Forcing the process down")
                self.kill()

        logger.info(f"Stopped Server {server_name} with PID {server_pid}")
        console.info(f"Stopped Server {server_name} with PID {server_pid}")

        # massive resetting of variables
        self.cleanup_server_object()
        server_users = server_permissions.get_server_user_list(self.server_id)

        self.stats.record_stats()

        for user in server_users:
            websocket_helper.broadcast_user(user, 'send_start_reload', {
                })

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
        if not self.check_running() and command.lower() != 'start':
            logger.warning(f"Server not running, unable to send command \"{command}\"")
            return False
        console.info(f"COMMAND TIME: {command}")
        logger.debug(f"Sending command {command} to server")

        # send it
        self.process.stdin.write(f"{command}\n".encode('utf-8'))
        self.process.stdin.flush()

    def crash_detected(self, name):

        # clear the old scheduled watcher task
        self.server_scheduler.remove_job(f"c_{self.server_id}")

        # the server crashed, or isn't found - so let's reset things.
        logger.warning(f"The server {name} seems to have vanished unexpectedly, did it crash?")

        if self.settings['crash_detection']:
            logger.warning(f"The server {name} has crashed and will be restarted. Restarting server")
            console.warning(f"The server {name} has crashed and will be restarted. Restarting server")
            self.run_threaded_server(None)
            return True
        else:
            logger.critical(f"The server {name} has crashed, crash detection is disabled and it will not be restarted")
            console.critical(f"The server {name} has crashed, crash detection is disabled and it will not be restarted")
            return False

    def kill(self):
        logger.info(f"Terminating server {self.server_id} and all child processes")
        process = psutil.Process(self.process.pid)

        # for every sub process...
        for proc in process.children(recursive=True):
            # kill all the child processes - it sounds too wrong saying kill all the children (kevdagoat: lol!)
            logger.info(f"Sending SIGKILL to server {proc.name}")
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

        logger.info(f"Detecting possible crash for server: {self.name} ")

        running = self.check_running()

        # if all is okay, we just exit out
        if running:
            return
        #check the exit code -- This could be a fix for /stop
        if self.process.returncode == 0:
            logger.warning(f'Process {self.process.pid} exited with code {self.process.returncode}. This is considered a clean exit'+
            ' supressing crash handling.')
            # cancel the watcher task
            self.server_scheduler.remove_job("c_"+str(self.server_id))
            return

        servers_helper.sever_crashed(self.server_id)
        # if we haven't tried to restart more 3 or more times
        if self.restart_count <= 3:

            # start the server if needed
            server_restarted = self.crash_detected(self.name)

            if server_restarted:
                # add to the restart count
                self.restart_count = self.restart_count + 1

        # we have tried to restart 4 times...
        elif self.restart_count == 4:
            logger.critical(f"Server {self.name} has been restarted {self.restart_count} times. It has crashed, not restarting.")
            console.critical(f"Server {self.name} has been restarted {self.restart_count} times. It has crashed, not restarting.")

            self.restart_count = 0
            self.is_crashed = True
            servers_helper.sever_crashed(self.server_id)

            # cancel the watcher task
            self.server_scheduler.remove_job("c_"+str(self.server_id))

    def remove_watcher_thread(self):
        logger.info("Removing old crash detection watcher thread")
        console.info("Removing old crash detection watcher thread")
        self.server_scheduler.remove_job('c_'+str(self.server_id))

    def agree_eula(self, user_id):
        file = os.path.join(self.server_path, 'eula.txt')
        f = open(file, 'w', encoding='utf-8')
        f.write('eula=true')
        f.close()
        self.run_threaded_server(user_id)

    def is_backup_running(self):
        if self.is_backingup:
            return True
        else:
            return False

    def backup_server(self):
        backup_thread = threading.Thread(target=self.a_backup_server, daemon=True, name=f"backup_{self.name}")
        logger.info(f"Starting Backup Thread for server {self.settings['server_name']}.")
        if self.server_path is None:
            self.server_path = helper.get_os_understandable_path(self.settings['path'])
            logger.info("Backup Thread - Local server path not defined. Setting local server path variable.")
        #checks if the backup thread is currently alive for this server
        if not self.is_backingup:
            try:
                backup_thread.start()
            except Exception as ex:
                logger.error(f"Failed to start backup: {ex}")
                return False
        else:
            logger.error(f"Backup is already being processed for server {self.settings['server_name']}. Canceling backup request")
            return False
        logger.info(f"Backup Thread started for server {self.settings['server_name']}.")

    def a_backup_server(self):
        logger.info(f"Starting server {self.name} (ID {self.server_id}) backup")
        self.is_backingup = True
        conf = management_helper.get_backup_config(self.server_id)
        try:
            backup_filename = f"{self.settings['backup_path']}/{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
            logger.info(f"Creating backup of server '{self.settings['server_name']}'" +
                        f" (ID#{self.server_id}, path={self.server_path}) at '{backup_filename}'")

            tempDir = tempfile.mkdtemp()
            shutil.copytree(self.server_path, tempDir, dirs_exist_ok=True)
            excluded_dirs = management_helper.get_excluded_backup_dirs(self.server_id)
            server_dir = helper.get_os_understandable_path(self.settings['path'])

            for my_dir in excluded_dirs:
                # Take the full path of the excluded dir and replace the server path with the temp path
                # This is so that we're only deleting excluded dirs from the temp path and not the server path
                excluded_dir = helper.get_os_understandable_path(my_dir).replace(server_dir, helper.get_os_understandable_path(tempDir))
                # Next, check to see if it is a directory
                if os.path.isdir(excluded_dir):
                    # If it is a directory, recursively delete the entire directory from the backup
                    shutil.rmtree(excluded_dir)
                else:
                    # If not, just remove the file
                    os.remove(excluded_dir)

            shutil.make_archive(helper.get_os_understandable_path(backup_filename), 'zip', tempDir)

            while len(self.list_backups()) > conf["max_backups"] and conf["max_backups"] > 0:
                backup_list = self.list_backups()
                oldfile = backup_list[0]
                oldfile_path = f"{conf['backup_path']}/{oldfile['path']}"
                logger.info(f"Removing old backup '{oldfile['path']}'")
                os.remove(helper.get_os_understandable_path(oldfile_path))

            self.is_backingup = False
            shutil.rmtree(tempDir)
            logger.info(f"Backup of server: {self.name} completed")
            return
        except:
            logger.exception(f"Failed to create backup of server {self.name} (ID {self.server_id})")
            self.is_backingup = False
            return

    def list_backups(self):
        if self.settings['backup_path']:
            if helper.check_path_exists(helper.get_os_understandable_path(self.settings['backup_path'])):
                files = (
                    helper.get_human_readable_files_sizes(helper.list_dir_by_date(helper.get_os_understandable_path(self.settings['backup_path']))))
                return [{
                         "path": os.path.relpath(f['path'],
                         start=helper.get_os_understandable_path(self.settings['backup_path'])),
                         "size": f["size"]
                        } for f in files]
            else:
                return []
        else:
            logger.info(f"Error putting backup file list for server with ID: {self.server_id}")
            return[]

    def jar_update(self):
        servers_helper.set_update(self.server_id, True)
        update_thread = threading.Thread(target=self.a_jar_update, daemon=True, name=f"exe_update_{self.name}")
        update_thread.start()

    def check_update(self):

        if servers_helper.get_server_stats_by_id(self.server_id)['updating']:
            return True
        else:
            return False

    def a_jar_update(self):
        wasStarted = "-1"
        self.backup_server()
        #checks if server is running. Calls shutdown if it is running.
        if self.check_running():
            wasStarted = True
            logger.info(f"Server with PID {self.process.pid} is running. Sending shutdown command")
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
            logger.info(f"Executable backup directory not found for Server: {self.name}. Creating one.")
            os.mkdir(backup_dir)
            backup_executable = os.path.join(backup_dir, 'old_server.jar')

            if os.path.isfile(backup_executable):
                #removes old backup
                logger.info(f"Old backup found for server: {self.name}. Removing...")
                os.remove(backup_executable)
                logger.info(f"Old backup removed for server: {self.name}.")
            else:
                logger.info(f"No old backups found for server: {self.name}")

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
                    server_users = server_permissions.get_server_user_list(self.server_id)
                    for user in server_users:
                        websocket_helper.broadcast_user(user, 'notification', "Executable update finished for " + self.name)
                    time.sleep(3)
                    websocket_helper.broadcast_page('/panel/server_detail', 'update_button_status', {
                        'isUpdating': self.check_update(),
                        'server_id': self.server_id,
                        'wasRunning': wasStarted
                    })
                    websocket_helper.broadcast_page('/panel/dashboard', 'send_start_reload', {
                    })
                server_users = server_permissions.get_server_user_list(self.server_id)
                for user in server_users:
                    websocket_helper.broadcast_user(user, 'notification', "Executable update finished for "+self.name)

                management_helper.add_to_audit_log_raw(
                    'Alert', '-1', self.server_id, "Executable update finished for "+self.name, self.settings['server_ip'])
                if wasStarted:
                    self.start_server()
            elif not downloaded and not self.is_backingup:
                time.sleep(5)
                server_users = server_permissions.get_server_user_list(self.server_id)
                for user in server_users:
                    websocket_helper.broadcast_user(user,'notification',
                                           "Executable update failed for " + self.name + ". Check log file for details.")
                logger.error("Executable download failed.")
