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


class Audit_Log(BaseModel):
    audit_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    user_name = CharField(default="")
    user_id = IntegerField(default=0)
    source_ip = CharField(default='127.0.0.1')
    server_id = IntegerField(default=None)
    log_msg = TextField(default='')


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
    server_ip = CharField(default="127.0.0.1")
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
    mem_percent = FloatField(default=0)
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
    executed = BooleanField(default=False)

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
                Commands,
                Audit_Log
            ])

    @staticmethod
    def default_settings():
        logger.info("Fresh Install Detected - Creating Default Settings")
        console.info("Fresh Install Detected - Creating Default Settings")
        default_data = helper.find_default_password()

        username = default_data.get("username", 'admin')
        password = default_data.get("password", 'crafty')
        api_token = helper.random_string_generator(32)
        
        Users.insert({
            Users.username: username.lower(),
            Users.password: helper.encode_pass(password),
            Users.api_token: api_token,
            Users.enabled: True
        }).execute()

        console.info("API token is {}".format(api_token))

    @staticmethod
    def is_fresh_install():
        try:
            user = Users.get_by_id(1)
            return False
        except:
            return True
            pass


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

    def get_server_data_by_id(self, server_id):
        try:
            query = Servers.get_by_id(server_id)
        except DoesNotExist:
            return {}

        return model_to_dict(query)

    def get_all_defined_servers(self):
        query = Servers.select()
        return self.return_rows(query)

    def get_all_servers_stats(self):
        servers = self.get_all_defined_servers()
        server_data = []

        for s in servers:
            latest = Server_Stats.select().where(Server_Stats.server_id == s.get('server_id')).order_by(Server_Stats.created.desc()).limit(1)
            server_data.append({'server_data': s, "stats": self.return_rows(latest)})
        return server_data

    def get_server_stats_by_id(self, server_id):
        stats = Server_Stats.select().where(Server_Stats.server_id == server_id).order_by(Server_Stats.created.desc()).limit(1)
        return self.return_rows(stats)

    def server_id_exists(self, server_id):
        if not self.get_server_data_by_id(server_id):
            return False
        return True

    @staticmethod
    def get_latest_hosts_stats():
        query = Host_Stats.select().order_by(Host_Stats.id.desc()).get()
        return model_to_dict(query)

    def get_all_users(self):
        query = Users.select()
        return query

    def get_unactioned_commands(self):
        query = Commands.select().where(Commands.executed == 0)
        return self.return_rows(query)

    def get_server_friendly_name(self, server_id):
        server_data = self.get_server_data_by_id(server_id)
        friendly_name = "{}-{}".format(server_data.get('server_id', 0), server_data.get('server_name', None))
        return friendly_name

    def send_command(self, user_id, server_id, remote_ip, command):

        server_name = self.get_server_friendly_name(server_id)

        self.add_to_audit_log(user_id, "Issued Command {} for Server: {}".format(command, server_name),
                              server_id, remote_ip)

        Commands.insert({
            Commands.server_id: server_id,
            Commands.user: user_id,
            Commands.source_ip: remote_ip,
            Commands.command: command
        }).execute()

    def get_actity_log(self):
        q = Audit_Log.select()
        return self.return_db_rows(q)

    def return_db_rows(self, model):
        data = [model_to_dict(row) for row in model]
        return data

    @staticmethod
    def mark_command_complete(command_id=None):
        if command_id is not None:
            logger.debug("Marking Command {} completed".format(command_id))
            Commands.update({
                Commands.executed: True
            }).where(Commands.command_id == command_id).execute()

    @staticmethod
    def add_to_audit_log(user_id, log_msg, server_id=None, source_ip=None):
        logger.debug("Adding to audit log User:{} - Message: {} ".format(user_id, log_msg))
        user_data = Users.get_by_id(user_id)

        audit_msg = "{} {}".format(str(user_data.username).capitalize(), log_msg)

        Audit_Log.insert({
            Audit_Log.user_name: user_data.username,
            Audit_Log.user_id: user_id,
            Audit_Log.server_id: server_id,
            Audit_Log.log_msg: audit_msg,
            Audit_Log.source_ip: source_ip
        }).execute()




installer = db_builder()
db_helper = db_shortcuts()
