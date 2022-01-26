import os
import sys
import json
import time
import argparse
import logging.config
import signal
from app.classes.shared.console import console
from app.classes.shared.helpers import helper
if helper.check_file_exists('/.dockerenv'):
    console.cyan("Docker environment detected!")
else:
    if helper.checkRoot():
        console.critical("Root detected. Root/Admin access denied. Run Crafty again with non-elevated permissions.")
        time.sleep(5)
        console.critical("Crafty shutting down. Root/Admin access denied.")
        sys.exit(0)
# pylint: disable=wrong-import-position
from app.classes.shared.main_models import installer, database
from app.classes.shared.tasks import TasksManager
from app.classes.shared.main_controller import Controller
from app.classes.shared.migration import MigrationManager

from app.classes.shared.command import MainPrompt


def do_intro():
    logger.info("***** Crafty Controller Started *****")

    version = helper.get_version_string()

    intro = f"""
    {'/' * 75}
    #{("Welcome to Crafty Controller - v." + version).center(73, " ")}#
    {'/' * 75}
    #{"Server Manager / Web Portal for your Minecraft server".center(73, " ")}#
    #{"Homepage: www.craftycontrol.com".center(73, " ")}#
    {'/' * 75}
    """

    console.magenta(intro)


def setup_logging(debug=True):
    logging_config_file = os.path.join(os.path.curdir,
                                       'app',
                                       'config',
                                       'logging.json'
                                       )

    if os.path.exists(logging_config_file):
        # open our logging config file
        with open(logging_config_file, 'rt', encoding='utf-8') as f:
            logging_config = json.load(f)
            if debug:
                logging_config['loggers']['']['level'] = 'DEBUG'

            logging.config.dictConfig(logging_config)

    else:
        logging.basicConfig(level=logging.DEBUG)
        logging.warning(f"Unable to read logging config from {logging_config_file}")
        console.critical(f"Unable to read logging config from {logging_config_file}")


# Our Main Starter
if __name__ == '__main__':
    parser = argparse.ArgumentParser("Crafty Controller - A Server Management System")

    parser.add_argument('-i', '--ignore',
                        action='store_true',
                        help="Ignore session.lock files"
                        )

    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help="Sets logging level to debug."
                        )

    parser.add_argument('-d', '--daemon',
                        action='store_true',
                        help="Runs Crafty in daemon mode (no prompt)"
                        )

    args = parser.parse_args()

    setup_logging(debug=args.verbose)

    # setting up the logger object
    logger = logging.getLogger(__name__)
    console.cyan(f"Logging set to: {logger.level}")

    # print our pretty start message
    do_intro()

    # our session file, helps prevent multiple controller agents on the same machine.
    helper.create_session_file(ignore=args.ignore)


    migration_manager = MigrationManager(database)
    migration_manager.up() # Automatically runs migrations

    # do our installer stuff
    fresh_install = installer.is_fresh_install()

    if fresh_install:
        console.debug("Fresh install detected")
        console.warning("We have detected a fresh install. Please be sure to forward Crafty's port, " +
        f"{helper.get_setting('https_port')}, through your router/firewall if you would like to be able to access Crafty remotely.")
        installer.default_settings()
    else:
        console.debug("Existing install detected")

    # now the tables are created, we can load the tasks_manger and server controller
    controller = Controller()
    tasks_manager = TasksManager(controller)
    tasks_manager.start_webserver()

    # slowing down reporting just for a 1/2 second so messages look cleaner
    time.sleep(.5)

    # init servers
    logger.info("Initializing all servers defined")
    console.info("Initializing all servers defined")
    controller.init_all_servers()
    servers = controller.list_defined_servers()

    # start stats logging
    tasks_manager.start_stats_recording()

    # once the controller is up and stats are logging, we can kick off the scheduler officially
    tasks_manager.start_scheduler()

    # refresh our cache and schedule for every 12 hoursour cache refresh for serverjars.com
    tasks_manager.serverjar_cache_refresher()

    logger.info("Checking Internet. This may take a minute.")
    console.info("Checking Internet. This may take a minute.")

    if not helper.check_internet():
        console.warning("We have detected the machine running Crafty has no connection to the internet. " +
        "Client connections to the server may be limited.")

    if not controller.check_system_user():
        controller.add_system_user()

    Crafty = MainPrompt(tasks_manager, migration_manager)

    project_root = os.path.dirname(__file__)
    controller.set_project_root(project_root)

    def sigterm_handler():
        print() # for newline
        logger.info("Recieved SIGTERM, stopping Crafty")
        console.info("Recieved SIGTERM, stopping Crafty")
        tasks_manager._main_graceful_exit()
        Crafty.universal_exit()

    signal.signal(signal.SIGTERM, sigterm_handler)

    if not args.daemon:
        try:
            Crafty.cmdloop()
        except KeyboardInterrupt:
            print() # for newline
            logger.info("Recieved SIGINT, stopping Crafty")
            console.info("Recieved SIGINT, stopping Crafty")
            tasks_manager._main_graceful_exit()
            Crafty.universal_exit()
    else:
        print("Crafty started in daemon mode, no shell will be printed")
        while True:
            try:
                if tasks_manager.get_main_thread_run_status():
                    break
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Recieved SIGINT, stopping Crafty")
                console.info("Recieved SIGINT, stopping Crafty")
                break
        tasks_manager._main_graceful_exit()
        Crafty.universal_exit()
