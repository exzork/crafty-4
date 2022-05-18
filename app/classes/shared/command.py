import sys
import cmd
import time
import threading
import logging
from app.classes.shared.console import Console

from app.classes.shared.import3 import Import3

logger = logging.getLogger(__name__)


class MainPrompt(cmd.Cmd):
    def __init__(self, helper, tasks_manager, migration_manager):
        super().__init__()
        self.helper = helper
        self.tasks_manager = tasks_manager
        self.migration_manager = migration_manager
        # overrides the default Prompt
        self.prompt = f"Crafty Controller v{self.helper.get_version_string()} > "

    # see MR !233 for pylint exemptino reason
    @staticmethod
    def emptyline():  # pylint: disable=arguments-differ
        pass

    def do_exit(self, _line):
        self.tasks_manager._main_graceful_exit()
        self.universal_exit()

    def do_migrations(self, line):
        if line == "up":
            self.migration_manager.up()
        elif line == "down":
            self.migration_manager.down()
        elif line == "done":
            Console.info(self.migration_manager.done)
        elif line == "todo":
            Console.info(self.migration_manager.todo)
        elif line == "diff":
            Console.info(self.migration_manager.diff)
        elif line == "info":
            Console.info(f"Done: {self.migration_manager.done}")
            Console.info(f"FS:   {self.migration_manager.todo}")
            Console.info(f"Todo: {self.migration_manager.diff}")
        elif line.startswith("add "):
            migration_name = line[len("add ") :]
            self.migration_manager.create(migration_name, False)
        else:
            Console.info("Unknown migration command")

    @staticmethod
    def do_threads(_line):
        for thread in threading.enumerate():
            if sys.version_info >= (3, 8):
                print(
                    f"Name: {thread.name} Identifier: "
                    f"{thread.ident} TID/PID: {thread.native_id}"
                )
            else:
                print(f"Name: {thread.name} Identifier: {thread.ident}")

    def do_import3(self, _line):
        Import3.start_import()

    def universal_exit(self):
        logger.info("Stopping all server daemons / threads")
        Console.info(
            "Stopping all server daemons / threads - This may take a few seconds"
        )
        self.helper.websocket_helper.disconnect_all()
        Console.info("Waiting for main thread to stop")
        while True:
            if self.tasks_manager.get_main_thread_run_status():
                sys.exit(0)
            time.sleep(1)

    def help_exit(self):
        Console.help("Stops the server if running, Exits the program")

    def help_migrations(self):
        Console.help("Only for advanced users. Use with caution")

    def help_import3(self):
        Console.help("Import users and servers from Crafty 3")
