import sys
import logging
import datetime

from app.classes.shared.helpers import helper
from app.classes.shared.console import console
from app.classes.shared.main_models import db_helper

from app.classes.models.users import Users, users_helper
from app.classes.models.servers import Servers
from app.classes.models.server_permissions import server_permissions

from app.classes.web.websocket_helper import websocket_helper

logger = logging.getLogger(__name__)
peewee_logger = logging.getLogger('peewee')
peewee_logger.setLevel(logging.INFO)

try:
    from peewee import SqliteDatabase, Model, ForeignKeyField, CharField, IntegerField, DateTimeField, FloatField, TextField, AutoField, BooleanField
    from playhouse.shortcuts import model_to_dict

except ModuleNotFoundError as e:
    logger.critical(f"Import Error: Unable to load {e.name} module", exc_info=True)
    console.critical(f"Import Error: Unable to load {e.name} module")
    sys.exit(1)

database = SqliteDatabase(helper.db_path, pragmas={
    'journal_mode': 'wal',
    'cache_size': -1024 * 10})

#************************************************************************************************
#                                   Audit_Log Class
#************************************************************************************************
class Audit_Log(Model):
    audit_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    user_name = CharField(default="")
    user_id = IntegerField(default=0, index=True)
    source_ip = CharField(default='127.0.0.1')
    server_id = IntegerField(default=None, index=True) # When auditing global events, use server ID 0
    log_msg = TextField(default='')

    class Meta:
        database = database


#************************************************************************************************
#                                   Host_Stats Class
#************************************************************************************************
class Host_Stats(Model):
    time = DateTimeField(default=datetime.datetime.now, index=True)
    boot_time = CharField(default="")
    cpu_usage = FloatField(default=0)
    cpu_cores = IntegerField(default=0)
    cpu_cur_freq = FloatField(default=0)
    cpu_max_freq = FloatField(default=0)
    mem_percent = FloatField(default=0)
    mem_usage = CharField(default="")
    mem_total = CharField(default="")
    disk_json = TextField(default="")

    class Meta:
        table_name = "host_stats"
        database = database


#************************************************************************************************
#                                   Commands Class
#************************************************************************************************
class Commands(Model):
    command_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    server_id = ForeignKeyField(Servers, backref='server', index=True)
    user = ForeignKeyField(Users, backref='user', index=True)
    source_ip = CharField(default='127.0.0.1')
    command = CharField(default='')
    executed = BooleanField(default=False)

    class Meta:
        table_name = "commands"
        database = database


#************************************************************************************************
#                                   Webhooks Class
#************************************************************************************************
class Webhooks(Model):
    id = AutoField()
    name = CharField(max_length=64, unique=True, index=True)
    method = CharField(default="POST")
    url = CharField(unique=True)
    event = CharField(default="")
    send_data = BooleanField(default=True)

    class Meta:
        table_name = "webhooks"
        database = database


#************************************************************************************************
#                                   Schedules Class
#************************************************************************************************
class Schedules(Model):
    schedule_id = IntegerField(unique=True, primary_key=True)
    server_id = ForeignKeyField(Servers, backref='schedule_server')
    enabled = BooleanField()
    action = CharField()
    interval = IntegerField()
    interval_type = CharField()
    start_time = CharField(null=True)
    command = CharField(null=True)
    comment = CharField()
    one_time = BooleanField(default=False)
    cron_string = CharField(default="")

    class Meta:
        table_name = 'schedules'
        database = database


#************************************************************************************************
#                                   Backups Class
#************************************************************************************************
class Backups(Model):
    directories = CharField(null=True)
    max_backups = IntegerField()
    server_id = ForeignKeyField(Servers, backref='backups_server')
    class Meta:
        table_name = 'backups'
        database = database

class helpers_management:

    #************************************************************************************************
    #                                   Host_Stats Methods
    #************************************************************************************************
    @staticmethod
    def get_latest_hosts_stats():
        query = Host_Stats.select().order_by(Host_Stats).get()
        return model_to_dict(query)

    #************************************************************************************************
    #                                   Commands Methods
    #************************************************************************************************
    @staticmethod
    def add_command(server_id, user_id, remote_ip, command):
        Commands.insert({
            Commands.server_id: server_id,
            Commands.user: user_id,
            Commands.source_ip: remote_ip,
            Commands.command: command
        }).execute()

    @staticmethod
    def get_unactioned_commands():
        query = Commands.select().where(Commands.executed == 0)
        return query

    @staticmethod
    def mark_command_complete(command_id=None):
        if command_id is not None:
            logger.debug(f"Marking Command {command_id} completed")
            Commands.update({
                Commands.executed: True
            }).where(Commands.command_id == command_id).execute()

    #************************************************************************************************
    #                                   Audit_Log Methods
    #************************************************************************************************
    @staticmethod
    def get_actity_log():
        q = Audit_Log.select()
        return db_helper.return_db_rows(q)

    @staticmethod
    def add_to_audit_log(user_id, log_msg, server_id=None, source_ip=None):
        logger.debug(f"Adding to audit log User:{user_id} - Message: {log_msg} ")
        user_data = users_helper.get_user(user_id)

        audit_msg = f"{str(user_data['username']).capitalize()} {log_msg}"

        server_users = server_permissions.get_server_user_list(server_id)
        for user in server_users:
            websocket_helper.broadcast_user(user,'notification', audit_msg)

        Audit_Log.insert({
            Audit_Log.user_name: user_data['username'],
            Audit_Log.user_id: user_id,
            Audit_Log.server_id: server_id,
            Audit_Log.log_msg: audit_msg,
            Audit_Log.source_ip: source_ip
        }).execute()
        #deletes records when they're more than 100
        ordered = Audit_Log.select().order_by(+Audit_Log.created)
        for item in ordered:
            #configurable through app/config/config.json
            if Audit_Log.select().count() > helper.get_setting('max_audit_entries'):
                Audit_Log.delete().where(Audit_Log.audit_id == item.audit_id).execute()
            else:
                return

    @staticmethod
    def add_to_audit_log_raw(user_name, user_id, server_id, log_msg, source_ip):
        Audit_Log.insert({
            Audit_Log.user_name: user_name,
            Audit_Log.user_id: user_id,
            Audit_Log.server_id: server_id,
            Audit_Log.log_msg: log_msg,
            Audit_Log.source_ip: source_ip
        }).execute()
        #deletes records when they're more than 100
        ordered = Audit_Log.select().order_by(+Audit_Log.created)
        for item in ordered:
            #configurable through app/config/config.json
            if Audit_Log.select().count() > helper.get_setting('max_audit_entries'):
                Audit_Log.delete().where(Audit_Log.audit_id == item.audit_id).execute()
            else:
                return
    #************************************************************************************************
    #                                  Schedules Methods
    #************************************************************************************************
    @staticmethod
    def create_scheduled_task(
        server_id,
        action,
        interval,
        interval_type,
        start_time,
        command,
        comment=None,
        enabled=True,
        one_time=False,
        cron_string='* * * * *'):
        sch_id = Schedules.insert({
            Schedules.server_id: server_id,
            Schedules.action: action,
            Schedules.enabled: enabled,
            Schedules.interval: interval,
            Schedules.interval_type: interval_type,
            Schedules.start_time: start_time,
            Schedules.command: command,
            Schedules.comment: comment,
            Schedules.one_time: one_time,
            Schedules.cron_string: cron_string

        }).execute()
        return sch_id

    @staticmethod
    def delete_scheduled_task(schedule_id):
        sch = Schedules.get(Schedules.schedule_id == schedule_id)
        return Schedules.delete_instance(sch)

    @staticmethod
    def update_scheduled_task(schedule_id, updates):
        Schedules.update(updates).where(Schedules.schedule_id == schedule_id).execute()

    @staticmethod
    def delete_scheduled_task_by_server(server_id):
        Schedules.delete().where(Schedules.server_id == int(server_id)).execute()

    @staticmethod
    def get_scheduled_task(schedule_id):
        return model_to_dict(Schedules.get(Schedules.schedule_id == schedule_id))

    @staticmethod
    def get_scheduled_task_model(schedule_id):
        return Schedules.select().where(Schedules.schedule_id == schedule_id).get()

    @staticmethod
    def get_schedules_by_server(server_id):
        return Schedules.select().where(Schedules.server_id == server_id).execute()

    @staticmethod
    def get_schedules_all():
        return Schedules.select().execute()

    @staticmethod
    def get_schedules_enabled():
        #pylint: disable=singleton-comparison
        return Schedules.select().where(Schedules.enabled == True).execute()

    #************************************************************************************************
    #                                   Backups Methods
    #************************************************************************************************
    @staticmethod
    def get_backup_config(server_id):
        try:
            row = Backups.select().where(Backups.server_id == server_id).join(Servers)[0]
            conf = {
                "backup_path": row.server_id.backup_path,
                "directories": row.directories,
                "max_backups": row.max_backups,
                "server_id": row.server_id.server_id
            }
        except IndexError:
            conf = {
                "backup_path": None,
                "directories": None,
                "max_backups": 0,
                "server_id": server_id
            }
        return conf

    @staticmethod
    def set_backup_config(server_id: int, backup_path: str = None, max_backups: int = None):
        logger.debug(f"Updating server {server_id} backup config with {locals()}")
        if Backups.select().where(Backups.server_id == server_id).count() != 0:
            new_row = False
            conf = {}
        else:
            conf = {
                "directories": None,
                "max_backups": 0,
                "server_id":   server_id
            }
            new_row = True
        if max_backups is not None:
            conf['max_backups'] = max_backups
        if not new_row:
            with database.atomic():
                if backup_path is not None:
                    u1 = Servers.update(backup_path=backup_path).where(Servers.server_id == server_id).execute()
                else:
                    u1 = 0
                u2 = Backups.update(conf).where(Backups.server_id == server_id).execute()
            logger.debug(f"Updating existing backup record.  {u1}+{u2} rows affected")
        else:
            with database.atomic():
                conf["server_id"] = server_id
                if backup_path is not None:
                    Servers.update(backup_path=backup_path).where(Servers.server_id == server_id)
                Backups.create(**conf)
            logger.debug("Creating new backup record.")


management_helper = helpers_management()
