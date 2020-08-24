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
from app.classes.shared.tasks import tasks_manager
from app.classes.minecraft.controller import controller


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


def setup_logging(debug=False):
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

    parser = argparse.ArgumentParser("Crafty Commander - A Server Management System")

    parser.add_argument('-i', '--ignore',
                        action='store_true',
                        help="Ignore session.lock files"
                        )

    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help="Sets logging level to debug."
                        )

    args = parser.parse_args()

    helper.ensure_logging_setup()

    setup_logging(debug=args.verbose)

    # setting up the logger object
    logger = logging.getLogger(__name__)

    # print our pretty start message
    do_intro()

    # our session file, helps prevent multiple commander agents on the same machine.
    helper.create_session_file(ignore=args.ignore)

    tasks_manager.start_webserver()
    tasks_manager.start_scheduler()

    # slowing down reporting just for a 1/2 second so messages look cleaner
    time.sleep(.5)

    # do our installer stuff
    if installer.is_fresh_install():
        installer.create_tables()
        installer.default_settings()

    # init servers
    logger.info("Initializing all servers defined")
    console.info("Initializing all servers defined")

    controller.init_all_servers()
    servers = controller.list_defined_servers()

    # start stats logging
    tasks_manager.start_stats_recording()

    # refresh our cache and schedule for every 12 hoursour cache refresh for serverjars.com
    tasks_manager.serverjar_cache_refresher()

    # this should always be last
    tasks_manager.start_main_kill_switch_watcher()



    # our main loop - eventually a shell
    while True:
        if tasks_manager.get_main_thread_run_status():
            sys.exit(0)
        time.sleep(1)
