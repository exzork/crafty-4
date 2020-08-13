import sys
import logging
import datetime

from app.classes.shared.helpers import helper
from app.classes.shared.console import console

logger = logging.getLogger(__name__)

try:
    from peewee import *
    from playhouse.shortcuts import model_to_dict

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
    disk_percent = FloatField(default=0)
    disk_usage = CharField(default="")
    disk_total = CharField(default="")

    class Meta:
        table_name = "host_stats"


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
                Webhooks
            ])

    @staticmethod
    def default_settings():
        Users.insert({
            Users.username: 'Admin',
            Users.password: helper.encode_pass('asdfasdf'),
            Users.api_token: helper.random_string_generator(32),
            Users.enabled: True
        }).execute()

    @staticmethod
    def is_fresh_install():
        if helper.check_file_exists(helper.db_path):
            return False

        return True

installer = db_builder()
