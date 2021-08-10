import os
import sys
import json
import time
import logging
import threading
import asyncio

from app.classes.shared.helpers import helper
from app.classes.shared.console import console
from app.classes.web.tornado import Webserver
from app.classes.web.websocket_helper import websocket_helper

from app.classes.minecraft.serverjars import server_jar_obj
from app.classes.shared.models import db_helper

logger = logging.getLogger(__name__)

try:
    import schedule

except ModuleNotFoundError as e:
    logger.critical("Import Error: Unable to load {} module".format(e.name), exc_info=True)
    console.critical("Import Error: Unable to load {} module".format(e.name))
    sys.exit(1)

scheduler_intervals = { 'seconds',
                        'minutes',
                        'hours',
                        'days',
                        'weeks',
                        'monday',
                        'tuesday',
                        'wednesday',
                        'thursday',
                        'friday',
                        'saturday',
                        'sunday'
                        }

class TasksManager:

    def __init__(self, controller):
        self.controller = controller
        self.tornado = Webserver(controller, self)

        self.webserver_thread = threading.Thread(target=self.tornado.run_tornado, daemon=True, name='tornado_thread')

        self.main_kill_switch_thread = threading.Thread(target=self.main_kill_switch, daemon=True, name="main_loop")
        self.main_thread_exiting = False

        self.schedule_thread = threading.Thread(target=self.scheduler_thread, daemon=True, name="scheduler")

        self.log_watcher_thread = threading.Thread(target=self.log_watcher, daemon=True, name="log_watcher")

        self.command_thread = threading.Thread(target=self.command_watcher, daemon=True, name="command_watcher")

        self.realtime_thread = threading.Thread(target=self.realtime, daemon=True, name="realtime")

        self.reload_schedule_from_db()


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

    def reload_schedule_from_db(self):
        jobs = db_helper.get_schedules_enabled()
        schedule.clear(tag='backup')
        schedule.clear(tag='db')
        for j in jobs:
            if j.interval_type in scheduler_intervals:
                logger.info("Loading schedule ID#{i}: '{a}' every {n} {t} at {s}".format(
                    i=j.schedule_id, a=j.action, n=j.interval, t=j.interval_type, s=j.start_time))
                try:
                    getattr(schedule.every(j.interval), j.interval_type).at(j.start_time).do(
                        db_helper.send_command, 0, j.server_id, "127.27.23.89", j.action)
                except schedule.ScheduleValueError as e:
                    logger.critical("Scheduler value error occurred: {} on ID#{}".format(e, j.schedule_id))
            else:
                logger.critical("Unknown schedule job type '{}' at id {}, skipping".format(j.interval_type, j.schedule_id))
    
    def command_watcher(self):
        while True:
            # select any commands waiting to be processed
            commands = db_helper.get_unactioned_commands()
            for c in commands:

                svr = self.controller.get_server_obj(c['server_id']['server_id'])
                command = c.get('command', None)

                if command == 'start_server':
                    svr.run_threaded_server()

                elif command == 'stop_server':
                    svr.stop_threaded_server()

                elif command == "restart_server":
                    svr.restart_threaded_server()

                elif command == "backup_server":
                    svr.backup_server()

                db_helper.mark_command_complete(c.get('command_id', None))

            time.sleep(1)

    def _main_graceful_exit(self):
        try:
            os.remove(helper.session_file)
            os.remove(os.path.join(helper.root_dir, 'exit.txt'))
            os.remove(os.path.join(helper.root_dir, '.header'))
            self.controller.stop_all_servers()
        except:
            logger.info("Caught error during shutdown", exc_info=True)

        logger.info("***** Crafty Shutting Down *****\n\n")
        console.info("***** Crafty Shutting Down *****\n\n")
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

    def start_scheduler(self):
        logger.info("Launching Scheduler Thread...")
        console.info("Launching Scheduler Thread...")
        self.schedule_thread.start()
        logger.info("Launching command thread...")
        console.info("Launching command thread...")
        self.command_thread.start()
        logger.info("Launching log watcher...")
        console.info("Launching log watcher...")
        self.log_watcher_thread.start()
        logger.info("Launching realtime thread...")
        console.info("Launching realtime thread...")
        self.realtime_thread.start()

    @staticmethod
    def scheduler_thread():
        while True:
            schedule.run_pending()
            time.sleep(1)

    def start_stats_recording(self):
        stats_update_frequency = helper.get_setting('stats_update_frequency')
        logger.info("Stats collection frequency set to {stats} seconds".format(stats=stats_update_frequency))
        console.info("Stats collection frequency set to {stats} seconds".format(stats=stats_update_frequency))

        # one for now,
        self.controller.stats.record_stats()

        # one for later
        schedule.every(stats_update_frequency).seconds.do(self.controller.stats.record_stats).tag('stats-recording')

    @staticmethod
    def serverjar_cache_refresher():
        logger.info("Refreshing serverjars.com cache on start")
        server_jar_obj.refresh_cache()

        logger.info("Scheduling Serverjars.com cache refresh service every 12 hours")
        schedule.every(12).hours.do(server_jar_obj.refresh_cache).tag('serverjars')

    @staticmethod
    def realtime():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        host_stats = db_helper.get_latest_hosts_stats()

        while True:

            if host_stats.get('cpu_usage') != \
                    db_helper.get_latest_hosts_stats().get('cpu_usage') or \
                    host_stats.get('mem_percent') != \
                    db_helper.get_latest_hosts_stats().get('mem_percent'):
                # Stats are different

                host_stats = db_helper.get_latest_hosts_stats()
                if len(websocket_helper.clients) > 0:
                    print('there are clients')
                    # There are clients
                    websocket_helper.broadcast_page('/panel/dashboard', 'update_host_stats', {
                        'cpu_usage': host_stats.get('cpu_usage'),
                        'cpu_cores': host_stats.get('cpu_cores'),
                        'cpu_cur_freq': host_stats.get('cpu_cur_freq'),
                        'cpu_max_freq': host_stats.get('cpu_max_freq'),
                        'mem_percent': host_stats.get('mem_percent'),
                        'mem_usage': host_stats.get('mem_usage')
                    })
            time.sleep(4)

    def log_watcher(self):
        helper.check_for_old_logs(db_helper)
        schedule.every(6).hours.do(lambda: helper.check_for_old_logs(db_helper)).tag('log-mgmt')

