import os
import sys
import cmd
import time
import threading
import logging

from app.classes.shared.tasks import TasksManager

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

    def __init__(self, tasks_manager, migration_manager):
        super().__init__()
        self.tasks_manager = tasks_manager
        self.migration_manager = migration_manager

    # overrides the default Prompt
    prompt = "Crafty Controller v{} > ".format(helper.get_version_string())

    @staticmethod
    def emptyline():
        pass

    def do_exit(self, line):
        self.tasks_manager._main_graceful_exit()
        self.universal_exit()
    
    def do_migrations(self, line):
        if line == 'up':
            self.migration_manager.up()
        elif line == 'down':
            self.migration_manager.down()
        elif line == 'done':
            console.info(self.migration_manager.done)
        elif line == 'todo':
            console.info(self.migration_manager.todo)
        elif line == 'diff':
            console.info(self.migration_manager.diff)
        elif line == 'info':
            console.info('Done: {}'.format(self.migration_manager.done))
            console.info('FS:   {}'.format(self.migration_manager.todo))
            console.info('Todo: {}'.format(self.migration_manager.diff))
        elif line.startswith('add '):
            migration_name = line[len('add '):]
            self.migration_manager.create(migration_name, False)
        else:
            console.info('Unknown migration command')

    @staticmethod
    def do_threads(_line):
        for thread in threading.enumerate():
            if sys.version_info >= (3, 8):
                print(f'Name: {thread.name} Identifier: {thread.ident} TID/PID: {thread.native_id}')
            else:
                print(f'Name: {thread.name} Identifier: {thread.ident}')

    def universal_exit(self):
        logger.info("Stopping all server daemons / threads")
        console.info("Stopping all server daemons / threads - This may take a few seconds")
        websocket_helper.disconnect_all()
        console.info('Waiting for main thread to stop')
        while True:
            if self.tasks_manager.get_main_thread_run_status():
                sys.exit(0)
            time.sleep(1)

    @staticmethod
    def help_exit():
        console.help("Stops the server if running, Exits the program")

    @staticmethod
    def help_migrations():
        console.help("Only for advanced users. Use with caution")
