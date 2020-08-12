import os
import sys
import json
import time
import logging
import threading


from app.classes.shared.helpers import helper
from app.classes.shared.console import console
from app.classes.web.tornado import webserver

logger = logging.getLogger(__name__)


class TasksManager:

    def __init__(self):
        self.tornado = webserver()
        self.webserver_thread = threading.Thread(target=self.tornado.run_tornado, daemon=True, name='tornado_thread')

        self.main_kill_switch_thread = threading.Thread(target=self.main_kill_switch, daemon=True, name="main_loop")
        self.main_thread_exiting = False

    def get_main_thread_run_status(self):
        return self.main_thread_exiting

    def start_main_kill_switch_watcher(self):
        self.main_kill_switch_thread.start()

    def main_kill_switch(self):
        while True:
            if os.path.exists(os.path.join(helper.root_dir, 'exit.txt')):
                logger.info("Found Exit File, stopping everything")
                self._main_graceful_exit()
            time.sleep(5)

    def _main_graceful_exit(self):
        # commander.stop_all_servers()
        logger.info("***** Crafty Shutting Down *****\n\n")
        console.info("***** Crafty Shutting Down *****\n\n")
        os.remove(helper.session_file)
        os.remove(os.path.join(helper.root_dir, 'exit.txt'))
        # ServerProps.cleanup()
        self.main_thread_exiting = True

    def start_webserver(self):
        self.webserver_thread.start()

    def reload_webserver(self):
        self.tornado.stop_web_server()
        console.info("Waiting 3 seconds")
        time.sleep(3)
        self.webserver_thread = threading.Thread(target=self.tornado.run_tornado, daemon=True, name='tornado_thread')
        self.start_webserver()

    def stop_webserver(self):
        self.tornado.stop_web_server()




tasks_manager = TasksManager()