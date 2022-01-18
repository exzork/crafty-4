from datetime import timedelta
import os
import sys
import json
import time
import logging
import threading
import asyncio
import shutil
from tzlocal import get_localzone

from app.classes.controllers.users_controller import Users_Controller

from app.classes.shared.helpers import helper
from app.classes.shared.console import console
from app.classes.web.tornado import Webserver
from app.classes.web.websocket_helper import websocket_helper

from app.classes.minecraft.serverjars import server_jar_obj
from app.classes.models.servers import servers_helper
from app.classes.models.management import management_helper
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, EVENT_ALL, EVENT_JOB_REMOVED

logger = logging.getLogger('apscheduler')

try:
    from apscheduler.schedulers.background import BackgroundScheduler

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

        tz = get_localzone()
        self.scheduler = BackgroundScheduler(timezone=str(tz))

        self.users_controller = Users_Controller()

        self.webserver_thread = threading.Thread(target=self.tornado.run_tornado, daemon=True, name='tornado_thread')

        self.main_thread_exiting = False

        self.schedule_thread = threading.Thread(target=self.scheduler_thread, daemon=True, name="scheduler")

        self.log_watcher_thread = threading.Thread(target=self.log_watcher, daemon=True, name="log_watcher")

        self.command_thread = threading.Thread(target=self.command_watcher, daemon=True, name="command_watcher")

        self.realtime_thread = threading.Thread(target=self.realtime, daemon=True, name="realtime")

        self.reload_schedule_from_db()


    def get_main_thread_run_status(self):
        return self.main_thread_exiting

    def reload_schedule_from_db(self):
        jobs = management_helper.get_schedules_enabled()
        logger.info("Reload from DB called. Current enabled schedules: ")
        for item in jobs:
            logger.info("JOB: {}".format(item))
    
    def command_watcher(self):
        while True:
            # select any commands waiting to be processed
            commands = management_helper.get_unactioned_commands()
            for c in commands:
                try:
                    svr = self.controller.get_server_obj(c.server_id)
                except:
                    logger.error("Server value requested does note exist purging item from waiting commands.")
                    management_helper.mark_command_complete(c.command_id)
                    
                user_id = c.user_id
                command = c.command

                if command == 'start_server':
                    svr.run_threaded_server(user_id)

                elif command == 'stop_server':
                    svr.stop_threaded_server()

                elif command == "restart_server":
                    svr.restart_threaded_server(user_id)

                elif command == "backup_server":
                    svr.backup_server()

                elif command == "update_executable":
                    svr.jar_update()
                else:
                    svr.send_command(command)
                management_helper.mark_command_complete(c.command_id)

            time.sleep(1)

    def _main_graceful_exit(self):
        try:
            os.remove(helper.session_file)
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

    def scheduler_thread(self):
        schedules = management_helper.get_schedules_enabled()
        self.scheduler.add_listener(self.schedule_watcher, mask=EVENT_JOB_EXECUTED)
        #self.scheduler.add_job(self.scheduler.print_jobs, 'interval', seconds=10, id='-1')
        #load schedules from DB
        for schedule in schedules:
            if schedule.cron_string != "":
                cron = schedule.cron_string.split(' ')
                self.scheduler.add_job(management_helper.add_command, 'cron', minute = cron[0],  hour = cron[1], day = cron[2], month = cron[3], day_of_week = cron[4], id=str(schedule.schedule_id), args=[schedule.server_id, self.users_controller.get_id_by_name('system'), '127.0.0.1', schedule.command])
            else:
                if schedule.interval_type == 'hours':
                    self.scheduler.add_job(management_helper.add_command, 'cron', minute = 0,  hour = '*/'+str(schedule.interval), id=str(schedule.schedule_id), args=[schedule.server_id, self.users_controller.get_id_by_name('system'), '127.0.0.1', schedule.command])
                elif schedule.interval_type == 'minutes':
                    self.scheduler.add_job(management_helper.add_command, 'cron', minute = '*/'+str(schedule.interval), id=str(schedule.schedule_id), args=[schedule.server_id, self.users_controller.get_id_by_name('system'), '127.0.0.1', schedule.command])
                elif schedule.interval_type == 'days':
                    time = schedule.start_time.split(':')
                    self.scheduler.add_job(management_helper.add_command, 'cron', day = '*/'+str(schedule.interval), hour=time[0], minute=time[1], id=str(schedule.schedule_id), args=[schedule.server_id, self.users_controller.get_id_by_name('system'), '127.0.0.1', schedule.command])

        self.scheduler.start()
        jobs = self.scheduler.get_jobs()
        logger.info("Loaded schedules. Current enabled schedules: ")
        for item in jobs:
            logger.info("JOB: {}".format(item))

    def schedule_job(self, job_data):
        sch_id = management_helper.create_scheduled_task(job_data['server_id'], job_data['action'], job_data['interval'], job_data['interval_type'], job_data['start_time'], job_data['command'], "None", job_data['enabled'], job_data['one_time'], job_data['cron_string'])
        if job_data['enabled']:
            if job_data['cron_string'] != "":
                cron = job_data['cron_string'].split(' ')
                try:
                    self.scheduler.add_job(management_helper.add_command, 'cron', minute = cron[0],  hour = cron[1], day = cron[2], month = cron[3], day_of_week = cron[4], id=str(sch_id), args=[job_data['server_id'], self.users_controller.get_id_by_name('system'), '127.0.0.1', job_data['command']])
                except Exception as e:
                    console.error("Failed to schedule task with error: {}.".format(e))
                    console.info("Removing failed task from DB.")
                    management_helper.delete_scheduled_task(sch_id)
            else:
                if job_data['interval_type'] == 'hours':
                    self.scheduler.add_job(management_helper.add_command, 'cron', minute = 0,  hour = '*/'+str(job_data['interval']), id=str(sch_id), args=[job_data['server_id'], self.users_controller.get_id_by_name('system'), '127.0.0.1', job_data['command']])
                elif job_data['interval_type'] == 'minutes':
                    self.scheduler.add_job(management_helper.add_command, 'cron', minute = '*/'+str(job_data['interval']), id=str(sch_id), args=[job_data['server_id'], self.users_controller.get_id_by_name('system'), '127.0.0.1', job_data['command']])
                elif job_data['interval_type'] == 'days':
                    time = job_data['start_time'].split(':')
                    self.scheduler.add_job(management_helper.add_command, 'cron', day = '*/'+str(job_data['interval']), hour = time[0], minute = time[1], id=str(sch_id), args=[job_data['server_id'], self.users_controller.get_id_by_name('system'), '127.0.0.1', job_data['command']], )
            logger.info("Added job. Current enabled schedules: ")
            jobs = self.scheduler.get_jobs()
            for item in jobs:
                logger.info("JOB: {}".format(item))

    def remove_all_server_tasks(self, server_id):
        schedules = management_helper.get_schedules_by_server(server_id)
        for schedule in schedules:
            self.remove_job(schedule.schedule_id)

    def remove_job(self, sch_id):
        job = management_helper.get_scheduled_task_model(sch_id)
        management_helper.delete_scheduled_task(sch_id)
        if job.enabled:
            self.scheduler.remove_job(str(sch_id))
            logger.info("Job with ID {} was deleted.".format(sch_id))
        else:
            logger.info("Job with ID {} was deleted from DB, but was not enabled. Not going to try removing something that doesn't exist from active schedules.".format(sch_id))

    def update_job(self, sch_id, job_data):
        management_helper.update_scheduled_task(sch_id, job_data)
        try:
            self.scheduler.remove_job(str(sch_id))
        except:
            logger.info("No job found in update job. Assuming it was previously disabled. Starting new job.")
            if job_data['cron_string'] != "":
                cron = job_data['cron_string'].split(' ')
                try:
                    self.scheduler.add_job(management_helper.add_command, 'cron', minute = cron[0],  hour = cron[1], day = cron[2], month = cron[3], day_of_week = cron[4], args=[job_data['server_id'], self.users_controller.get_id_by_name('system'), '127.0.0.1', job_data['command']])
                except Exception as e:
                    console.error("Failed to schedule task with error: {}.".format(e))
                    console.info("Removing failed task from DB.")
                    management_helper.delete_scheduled_task(sch_id)
            else:
                if job_data['interval_type'] == 'hours':
                    self.scheduler.add_job(management_helper.add_command, 'cron', minute = 0,  hour = '*/'+str(job_data['interval']), id=str(sch_id), args=[job_data['server_id'], self.users_controller.get_id_by_name('system'), '127.0.0.1', job_data['command']])
                elif job_data['interval_type'] == 'minutes':
                    self.scheduler.add_job(management_helper.add_command, 'cron', minute = '*/'+str(job_data['interval']), id=str(sch_id), args=[job_data['server_id'], self.users_controller.get_id_by_name('system'), '127.0.0.1', job_data['command']])
                elif job_data['interval_type'] == 'days':
                    time = job_data['start_time'].split(':')
                    self.scheduler.add_job(management_helper.add_command, 'cron', day = '*/'+str(job_data['interval']), hour = time[0], minute = time[1], id=str(sch_id), args=[job_data['server_id'], self.users_controller.get_id_by_name('system'), '127.0.0.1', job_data['command']], )
        else:
            try:
                self.scheduler.get_job(str(sch_id))
                self.scheduler.remove_job(str(sch_id))
            except:
                logger.info("APScheduler found no scheduled job on schedule update for schedule with id: {}. Assuming it was already disabled.".format(sch_id))

    def schedule_watcher(self, event):
        if not event.exception:
            if str(event.job_id).isnumeric():
                task = management_helper.get_scheduled_task_model(int(event.job_id))
                if task.one_time:
                    self.remove_job(task.schedule_id)
                    logger.info("one time task detected. Deleting...")
            else:
                logger.info("Event job ID is not numerical. Assuming it's stats - not stored in DB. Moving on.")
        else:
            logger.error("Task failed with error: {}".format(event.exception))

    def start_stats_recording(self):
        stats_update_frequency = helper.get_setting('stats_update_frequency')
        logger.info("Stats collection frequency set to {stats} seconds".format(stats=stats_update_frequency))
        console.info("Stats collection frequency set to {stats} seconds".format(stats=stats_update_frequency))

        # one for now,
        self.controller.stats.record_stats()
        # one for later
        self.scheduler.add_job(self.controller.stats.record_stats, 'interval', seconds=stats_update_frequency, id="stats")


    def serverjar_cache_refresher(self):
        logger.info("Refreshing serverjars.com cache on start")
        server_jar_obj.refresh_cache()

        logger.info("Scheduling Serverjars.com cache refresh service every 12 hours")
        self.scheduler.add_job(server_jar_obj.refresh_cache, 'interval', hours=12, id="serverjars")

    @staticmethod
    def realtime():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        host_stats = management_helper.get_latest_hosts_stats()

        while True:

            if host_stats.get('cpu_usage') != \
                    management_helper.get_latest_hosts_stats().get('cpu_usage') or \
                    host_stats.get('mem_percent') != \
                    management_helper.get_latest_hosts_stats().get('mem_percent'):
                # Stats are different

                host_stats = management_helper.get_latest_hosts_stats()
                if len(websocket_helper.clients) > 0:
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
        self.controller.servers.check_for_old_logs()
        self.scheduler.add_job(self.controller.servers.check_for_old_logs, 'interval', hours=6, id="log-mgmt")

