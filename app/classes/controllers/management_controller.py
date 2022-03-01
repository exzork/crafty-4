import logging

from app.classes.models.management import management_helper
from app.classes.models.servers import servers_helper

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
        management_helper.add_to_audit_log(user_id, f"issued command {command} for server {server_name}", server_id, remote_ip)
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
        return management_helper.create_scheduled_task(
                                                       server_id,
                                                       action,
                                                       interval,
                                                       interval_type,
                                                       start_time,
                                                       command,
                                                       comment,
                                                       enabled
                                                      )

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
    def get_child_schedules(sch_id):
        return management_helper.get_child_schedules(sch_id)

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
    def set_backup_config(server_id: int, backup_path: str = None, max_backups: int = None, excluded_dirs: list = None):
        return management_helper.set_backup_config(server_id, backup_path, max_backups, excluded_dirs)

    @staticmethod
    def get_excluded_backup_dirs(server_id: int):
        return management_helper.get_excluded_backup_dirs(server_id)

    @staticmethod
    def add_excluded_backup_dir(server_id: int, dir_to_add: str):
        management_helper.add_excluded_backup_dir(server_id, dir_to_add)

    @staticmethod
    def del_excluded_backup_dir(server_id: int, dir_to_del: str):
        management_helper.del_excluded_backup_dir(server_id, dir_to_del)
