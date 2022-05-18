import sys
import cmd
import time
import threading
import logging
import getpass
from app.classes.shared.console import Console

from app.classes.shared.import3 import Import3

logger = logging.getLogger(__name__)


class MainPrompt(cmd.Cmd):
    def __init__(self, helper, tasks_manager, migration_manager, main_controller):
        super().__init__()
        self.helper = helper
        self.tasks_manager = tasks_manager
        self.migration_manager = migration_manager
        self.controller = main_controller

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

    def do_set_passwd(self, line):

        try:
            username = str(line).lower()
            # If no user is found it returns None
            user_id = self.controller.users.get_id_by_name(username)
            if not username:
                Console.error("You must enter a username. Ex: `set_passwd admin'")
                return False
            if not user_id:
                Console.error(f"No user found by the name of {username}")
                return False
        except:
            Console.error(f"User: {line} Not Found")
            return False
        new_pass = getpass.getpass(prompt=f"NEW password for: {username} > ")
        new_pass_conf = getpass.getpass(prompt="Re-enter your password: > ")

        if new_pass != new_pass_conf:
            Console.error("Passwords do not match. Please try again.")
            return False

        if len(new_pass) > 512:
            Console.warning("Passwords must be greater than 6char long and under 512")
            return False

        if len(new_pass) < 6:
            Console.warning("Passwords must be greater than 6char long and under 512")
            return False
        self.controller.users.update_user(user_id, {"password": new_pass})

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
