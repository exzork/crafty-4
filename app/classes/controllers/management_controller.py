import os
import time
import logging
import sys
import yaml
import asyncio
import shutil
import tempfile
import zipfile
from distutils import dir_util

from app.classes.shared.helpers import helper
from app.classes.shared.console import console

from app.classes.models.management import management_helper
from app.classes.models.servers import servers_helper

from app.classes.shared.server import Server
from app.classes.minecraft.server_props import ServerProps
from app.classes.minecraft.serverjars import server_jar_obj
from app.classes.minecraft.stats import Stats

logger = logging.getLogger(__name__)

class Management_Controller:

    #************************************************************************************************
    #                                   Host_Stats Methods
    #************************************************************************************************
    @staticmethod
    def get_latest_hosts_stats():
        return management_helper.get_latest_hosts_stats()

    #************************************************************************************************
    #                                   Commands Methods
    #************************************************************************************************
    @staticmethod
    def get_unactioned_commands():
        return management_helper.get_unactioned_commands()

    @staticmethod
    def send_command(user_id, server_id, remote_ip, command):
        server_name = servers_helper.get_server_friendly_name(server_id)

        # Example: Admin issued command start_server for server Survival
        management_helper.add_to_audit_log(user_id, "issued command {} for server {}".format(command, server_name),
                              server_id, remote_ip)
        management_helper.add_command(server_id, user_id, remote_ip, command)

    @staticmethod
    def mark_command_complete(command_id=None):
        return management_helper.mark_command_complete(command_id)
            
    #************************************************************************************************
    #                                   Audit_Log Methods
    #************************************************************************************************
    @staticmethod
    def get_actity_log():
        return management_helper.get_actity_log()

    @staticmethod
    def add_to_audit_log(user_id, log_msg, server_id=None, source_ip=None):
        return management_helper.add_to_audit_log(user_id, log_msg, server_id, source_ip)

    @staticmethod
    def add_to_audit_log_raw(user_name, user_id, server_id, log_msg, source_ip):
        return management_helper.add_to_audit_log_raw(user_name, user_id, server_id, log_msg, source_ip)

    #************************************************************************************************
    #                                  Schedules Methods
    #************************************************************************************************
    @staticmethod
    def create_scheduled_task(server_id, action, interval, interval_type, start_time, command, comment=None, enabled=True):
        return management_helper.create_scheduled_task(server_id, action, interval, interval_type, start_time, command, comment, enabled)

    @staticmethod
    def delete_scheduled_task(schedule_id):
        return management_helper.delete_scheduled_task(schedule_id)

    @staticmethod
    def update_scheduled_task(schedule_id, updates):
        return management_helper.update_scheduled_task(schedule_id, updates)

    @staticmethod
    def get_scheduled_task(schedule_id):
        return management_helper.get_scheduled_task(schedule_id)

    @staticmethod
    def get_scheduled_task_model(schedule_id):
        return management_helper.get_scheduled_task_model(schedule_id)

    @staticmethod
    def get_schedules_by_server(server_id):
        return management_helper.get_schedules_by_server(server_id)

    @staticmethod
    def get_schedules_all():
        return management_helper.get_schedules_all()

    @staticmethod
    def get_schedules_enabled():
        return management_helper.get_schedules_enabled()

    #************************************************************************************************
    #                                   Backups Methods
    #************************************************************************************************
    @staticmethod
    def get_backup_config(server_id):
        return management_helper.get_backup_config(server_id)

    @staticmethod
    def set_backup_config(server_id: int, backup_path: str = None, max_backups: int = None):
        return management_helper.set_backup_config(server_id, backup_path, max_backups)
