import os
import sys
import cmd
import time

import logging

logger = logging.getLogger(__name__)

from app.classes.shared.console import console
from app.classes.shared.helpers import helper
from app.classes.web.websocket_helper import websocket_helper

try:
    import requests

except ModuleNotFoundError as e:
    logger.critical("Import Error: Unable to load {} module".format(e.name), exc_info=True)
    console.critical("Import Error: Unable to load {} module".format(e.name))
    sys.exit(1)


class MainPrompt(cmd.Cmd, object):

    def __init__(self, tasks_manager):
        super().__init__()
        self.tasks_manager = tasks_manager

    # overrides the default Prompt
    prompt = "Crafty Controller v{} > ".format(helper.get_version_string())

    def __init__(self, tasks_manager):
        super().__init__()
        self.tasks_manager = tasks_manager

    @staticmethod
    def emptyline():
        pass

    @staticmethod
    def _clean_shutdown():
        exit_file = os.path.join(helper.root_dir, "exit.txt")
        try:
            with open(exit_file, 'w') as f:
                f.write("exit")

        except Exception as e:
            logger.critical("Unable to write exit file due to error: {}".format(e))
            console.critical("Unable to write exit file due to error: {}".format(e))

    def do_exit(self, line):
        logger.info("Stopping all server daemons / threads")
        console.info("Stopping all server daemons / threads - This may take a few seconds")
        websocket_helper.disconnect_all()
        self._clean_shutdown()
        console.info('Waiting for main thread to stop')
        while True:
            if self.tasks_manager.get_main_thread_run_status():
                sys.exit(0)
            time.sleep(1)


    @staticmethod
    def help_exit():
        console.help("Stops the server if running, Exits the program")
