import os
import sys
import logging
import datetime

from app.classes.shared.helpers import helper
from app.classes.shared.console import console
from app.classes.minecraft.server_props import ServerProps

logger = logging.getLogger(__name__)

try:
    from peewee import *
    from playhouse.shortcuts import model_to_dict
    import yaml

except ModuleNotFoundError as e:
    logger.critical("Import Error: Unable to load {} module".format(e, e.name))
    console.critical("Import Error: Unable to load {} module".format(e, e.name))
    sys.exit(1)

database = SqliteDatabase(helper.db_path, pragmas={
    'journal_mode': 'wal',
    'cache_size': -1024 * 10})


class BaseModel(Model):
    class Meta:
        database = database

# todo: access logs


class Users(BaseModel):
    user_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    last_login = DateTimeField(default=datetime.datetime.now)
    last_ip = CharField(default="")
    username = CharField(default="")
    password = CharField(default="")
    enabled = BooleanField(default=True)
    api_token = CharField(default="")
    allowed_servers = CharField(default="[]")

    class Meta:
        table_name = "users"


class Host_Stats(BaseModel):
    time = DateTimeField(default=datetime.datetime.now)
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


class Servers(BaseModel):
    server_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    server_uuid = CharField(default="")
    server_name = CharField(default="Server")
    path = CharField(default="")
    executable = CharField(default="")
    log_path = CharField(default="")
    execution_command = CharField(default="")
    auto_start = BooleanField(default=0)
    auto_start_delay = IntegerField(default=10)
    crash_detection = BooleanField(default=0)
    stop_command = CharField(default="stop")
    server_port = IntegerField(default=25565)

    class Meta:
        table_name = "servers"


class Server_Stats(BaseModel):
    stats_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    server_id = ForeignKeyField(Servers, backref='server')
    started = CharField(default="")
    running = BooleanField(default=False)
    cpu = FloatField(default=0)
    mem = FloatField(default=0)
    world_name = CharField(default="")
    world_size = CharField(default="")
    server_port = IntegerField(default=25565)
    int_ping_results = CharField(default="")
    online = IntegerField(default=0)
    max = IntegerField(default=0)
    players = CharField(default="")
    desc = CharField(default="Unable to Connect")
    version = CharField(default="")


    class Meta:
        table_name = "server_stats"


class Commands(BaseModel):
    command_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    server_id = ForeignKeyField(Servers, backref='server')
    user = ForeignKeyField(Users, backref='user')
    source_ip = CharField(default='127.0.0.1')
    command = CharField(default='')

    class Meta:
        table_name = "commands"


class Webhooks(BaseModel):
    id = AutoField()
    name = CharField(max_length=64, unique=True)
    method = CharField(default="POST")
    url = CharField(unique=True)
    event = CharField(default="")
    send_data = BooleanField(default=True)

    class Meta:
        table_name = "webhooks"


class Backups(BaseModel):
    directories = CharField()
    storage_location = CharField()
    max_backups = IntegerField()
    server_id = IntegerField()

    class Meta:
        table_name = 'backups'


class db_builder:

    @staticmethod
    def create_tables():
        with database:
            database.create_tables([
                Backups,
                Users,
                Host_Stats,
                Webhooks,
                Servers,
                Server_Stats,
                Commands
            ])

    @staticmethod
    def default_settings():

        default_data = helper.find_default_password()

        username = default_data.get("username", 'Admin')
        password = default_data.get("password", 'crafty')

        Users.insert({
            Users.username: username,
            Users.password: helper.encode_pass(password),
            Users.api_token: helper.random_string_generator(32),
            Users.enabled: True
        }).execute()

    @staticmethod
    def is_fresh_install():
        if helper.check_file_exists(helper.db_path):
            return False
        return True


class db_shortcuts:

    def return_rows(self, query):
        rows = []

        try:
            if query.count() > 0:
                for s in query:
                    rows.append(model_to_dict(s))
        except Exception as e:
            logger.warning("Database Error: {}".format(e))
            pass

        return rows

    def get_all_defined_servers(self):
        query = Servers.select()
        return self.return_rows(query)

    def get_all_servers_stats(self):
        query = Server_Stats.select().order_by(Server_Stats.stats_id.desc()).limit(1)
        return self.return_rows(query)

    def get_latest_hosts_stats(self):
        query = Host_Stats.select().order_by(Host_Stats.id.desc()).get()
        return model_to_dict(query)


installer = db_builder()
db_helper = db_shortcuts()
