import os
import sys
import json
import time
import argparse
import logging.config

""" Our custom classes / pip packages """
from app.classes.shared.console import console
from app.classes.shared.helpers import helper
from app.classes.shared.models import installer

from app.classes.shared.tasks import TasksManager
from app.classes.shared.controller import Controller

from app.classes.shared.cmd import MainPrompt


def do_intro():
    logger.info("***** Crafty Controller Started *****")

    version = helper.get_version_string()

    intro = """
    {lines}
    #\t\tWelcome to Crafty Controller - v.{version}\t\t      #
    {lines}
    #   \tServer Manager / Web Portal for your Minecraft server \t      #
    #   \t\tHomepage: www.craftycontrol.com\t\t\t      #
    {lines}
    """.format(lines="/" * 75, version=version)

    console.magenta(intro)


def setup_logging(debug=True):
    logging_config_file = os.path.join(os.path.curdir,
                                       'app',
                                       'config',
                                       'logging.json'
                                       )

    if os.path.exists(logging_config_file):
        # open our logging config file
        with open(logging_config_file, 'rt') as f:
            logging_config = json.load(f)
            if debug:
                logging_config['loggers']['']['level'] = 'DEBUG'

            logging.config.dictConfig(logging_config)

    else:
        logging.basicConfig(level=logging.DEBUG)
        logging.warning("Unable to read logging config from {}".format(logging_config_file))
        console.critical("Unable to read logging config from {}".format(logging_config_file))


""" Our Main Starter """
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

    helper.ensure_logging_setup()

    setup_logging(debug=args.verbose)

    # setting up the logger object
    logger = logging.getLogger(__name__)
    print("Logging set to: {} ".format(logger.level))

    # print our pretty start message
    do_intro()

    # our session file, helps prevent multiple controller agents on the same machine.
    helper.create_session_file(ignore=args.ignore)

    # do our installer stuff
    fresh_install = installer.is_fresh_install()

    if fresh_install:
        console.debug("Fresh install detected")
        installer.create_tables()
        installer.default_settings()
    else:
        console.debug("Existing install detected")
        installer.check_schema_version()

<<<<<<< HEAD
    # init servers
    logger.info("Initializing all servers defined")
    console.info("Initializing all servers defined")

    controller.init_all_servers()
    servers = controller.list_defined_servers()

    # now the tables are created, we can load the tasks_manger
    tasks_manager = TasksManager()

=======
    # now the tables are created, we can load the tasks_manger and server controller
    controller = Controller()
    tasks_manager = TasksManager(controller)
>>>>>>> backups-and-stuff
    tasks_manager.start_webserver()

    # slowing down reporting just for a 1/2 second so messages look cleaner
    time.sleep(.5)

<<<<<<< HEAD
=======
    # init servers
    logger.info("Initializing all servers defined")
    console.info("Initializing all servers defined")
    controller.init_all_servers()
    servers = controller.list_defined_servers()

>>>>>>> backups-and-stuff
    # start stats logging
    tasks_manager.start_stats_recording()

    # once the controller is up and stats are logging, we can kick off the scheduler officially
    tasks_manager.start_scheduler()

    # refresh our cache and schedule for every 12 hoursour cache refresh for serverjars.com
    tasks_manager.serverjar_cache_refresher()

    # this should always be last
    tasks_manager.start_main_kill_switch_watcher()

    Crafty = MainPrompt(tasks_manager)
<<<<<<< HEAD
    if not args.daemon:
        Crafty.cmdloop()
    else:
        print("Crafty started in daemon mode, no shell will be printed")
        while True:
            try:
                if tasks_manager.get_main_thread_run_status():
                    break
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Recieved SIGTERM, stopping Crafty")
                break
       
        logger.info("Stopping all server daemons / threads")
        console.info("Stopping all server daemons / threads - This may take a few seconds")
        Crafty._clean_shutdown()
        while True:
            if tasks_manager.get_main_thread_run_status():
                sys.exit(0)
        time.sleep(1)
=======
    Crafty.cmdloop()

    # our main loop - eventually a shell
    # while True:
    #     if tasks_manager.get_main_thread_run_status():
    #         sys.exit(0)
    #     time.sleep(1)
>>>>>>> backups-and-stuff
