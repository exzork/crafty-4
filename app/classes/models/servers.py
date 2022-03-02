import sys
import logging
import datetime

from app.classes.shared.helpers import helper
from app.classes.shared.console import console
from app.classes.shared.main_models import db_helper

logger = logging.getLogger(__name__)
peewee_logger = logging.getLogger('peewee')
peewee_logger.setLevel(logging.INFO)

try:
    from peewee import SqliteDatabase, Model, ForeignKeyField, CharField, AutoField, DateTimeField, BooleanField, IntegerField, FloatField

except ModuleNotFoundError as e:
    logger.critical(f"Import Error: Unable to load {e.name} module", exc_info=True)
    console.critical(f"Import Error: Unable to load {e.name} module")
    sys.exit(1)

database = SqliteDatabase(helper.db_path, pragmas={
    'journal_mode': 'wal',
    'cache_size': -1024 * 10})

#************************************************************************************************
#                                   Servers Class
#************************************************************************************************
class Servers(Model):
    server_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    server_uuid = CharField(default="", index=True)
    server_name = CharField(default="Server", index=True)
    path = CharField(default="")
    backup_path = CharField(default="")
    executable = CharField(default="")
    log_path = CharField(default="")
    execution_command = CharField(default="")
    auto_start = BooleanField(default=0)
    auto_start_delay = IntegerField(default=10)
    crash_detection = BooleanField(default=0)
    stop_command = CharField(default="stop")
    executable_update_url = CharField(default="")
    server_ip = CharField(default="127.0.0.1")
    server_port = IntegerField(default=25565)
    logs_delete_after = IntegerField(default=0)
    type = CharField(default="minecraft-java")

    class Meta:
        table_name = "servers"
        database = database


#************************************************************************************************
#                                   Servers Stats Class
#************************************************************************************************
class Server_Stats(Model):
    stats_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    server_id = ForeignKeyField(Servers, backref='server', index=True)
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
    updating = BooleanField(default=False)
    waiting_start = BooleanField(default=False)
    first_run = BooleanField(default=True)
    crashed = BooleanField(default=False)


    class Meta:
        table_name = "server_stats"
        database = database


#************************************************************************************************
#                                   Servers Class
#************************************************************************************************
class helper_servers:

    #************************************************************************************************
    #                                   Generic Servers Methods
    #************************************************************************************************
    @staticmethod
    def create_server(
        name: str,
        server_uuid: str,
        server_dir: str,
        backup_path: str,
        server_command: str,
        server_file: str,
        server_log_file: str,
        server_stop: str,
        server_type: str,
        server_port=25565):
        return Servers.insert({
            Servers.server_name: name,
            Servers.server_uuid: server_uuid,
            Servers.path: server_dir,
            Servers.executable: server_file,
            Servers.execution_command: server_command,
            Servers.auto_start: False,
            Servers.auto_start_delay: 10,
            Servers.crash_detection: False,
            Servers.log_path: server_log_file,
            Servers.server_port: server_port,
            Servers.stop_command: server_stop,
            Servers.backup_path: backup_path,
            Servers.type: server_type
        }).execute()


    @staticmethod
    def get_server_obj(server_id):
        return Servers.get_by_id(server_id)

    @staticmethod
    def get_server_type_by_id(server_id):
        server_type = Servers.select().where(Servers.server_id == server_id).get()
        return server_type.type

    @staticmethod
    def update_server(server_obj):
        return server_obj.save()

    @staticmethod
    def remove_server(server_id):
        with database.atomic():
            Servers.delete().where(Servers.server_id == server_id).execute()

    @staticmethod
    def get_server_data_by_id(server_id):
        query = Servers.select().where(Servers.server_id == server_id).limit(1)
        try:
            return db_helper.return_rows(query)[0]
        except IndexError:
            return {}

    #************************************************************************************************
    #                                     Servers Methods
    #************************************************************************************************
    @staticmethod
    def get_all_defined_servers():
        query = Servers.select()
        return db_helper.return_rows(query)

    @staticmethod
    def get_all_servers_stats():
        servers = servers_helper.get_all_defined_servers()
        server_data = []
        try:
            for s in servers:
                latest = Server_Stats.select().where(Server_Stats.server_id == s.get('server_id')).order_by(Server_Stats.created.desc()).limit(1)
                server_data.append({'server_data': s, "stats": db_helper.return_rows(latest)[0], "user_command_permission":True})
        except IndexError as ex:
            logger.error(f"Stats collection failed with error: {ex}. Was a server just created?")
        return server_data

    @staticmethod
    def get_server_friendly_name(server_id):
        server_data = servers_helper.get_server_data_by_id(server_id)
        friendly_name = f"{server_data.get('server_name', None)} with ID: {server_data.get('server_id', 0)}"
        return friendly_name

    #************************************************************************************************
    #                                    Servers_Stats Methods
    #************************************************************************************************
    @staticmethod
    def get_latest_server_stats(server_id):
        return Server_Stats.select().where(Server_Stats.server_id == server_id).order_by(Server_Stats.created.desc()).limit(1)

    @staticmethod
    def get_server_stats_by_id(server_id):
        stats = Server_Stats.select().where(Server_Stats.server_id == server_id).order_by(Server_Stats.created.desc()).limit(1)
        return db_helper.return_rows(stats)[0]

    @staticmethod
    def server_id_exists(server_id):
        if not servers_helper.get_server_data_by_id(server_id):
            return False
        return True

    @staticmethod
    def sever_crashed(server_id):
        with database.atomic():
            Server_Stats.update(crashed=True).where(Server_Stats.server_id == server_id).execute()

    @staticmethod
    def server_crash_reset(server_id):
        with database.atomic():
            Server_Stats.update(crashed=False).where(Server_Stats.server_id == server_id).execute()

    @staticmethod
    def is_crashed(server_id):
        svr = Server_Stats.select().where(Server_Stats.server_id == server_id).get()
        #pylint: disable=singleton-comparison
        if svr.crashed == True:
            return True
        else:
            return False

    @staticmethod
    def set_update(server_id, value):
        try:
            #Checks if server even exists
            Server_Stats.select().where(Server_Stats.server_id == server_id)
        except Exception as ex:
            logger.error(f"Database entry not found! {ex}")
        with database.atomic():
            Server_Stats.update(updating=value).where(Server_Stats.server_id == server_id).execute()

    @staticmethod
    def get_update_status(server_id):
        update_status = Server_Stats.select().where(Server_Stats.server_id == server_id).get()
        return update_status.updating

    @staticmethod
    def set_first_run(server_id):
        #Sets first run to false
        try:
            #Checks if server even exists
            Server_Stats.select().where(Server_Stats.server_id == server_id)
        except Exception as ex:
            logger.error(f"Database entry not found! {ex}")
            return
        with database.atomic():
            Server_Stats.update(first_run=False).where(Server_Stats.server_id == server_id).execute()

    @staticmethod
    def get_first_run(server_id):
        first_run = Server_Stats.select().where(Server_Stats.server_id == server_id).get()
        return first_run.first_run

    @staticmethod
    def get_TTL_without_player(server_id):
        last_stat = Server_Stats.select().where(Server_Stats.server_id == server_id).order_by(Server_Stats.created.desc()).first()
        last_stat_with_player = (Server_Stats
                                .select()
                                .where(Server_Stats.server_id == server_id)
                                .where(Server_Stats.online > 0)
                                .order_by(Server_Stats.created.desc())
                                .first())
        return last_stat.created - last_stat_with_player.created

    @staticmethod
    def can_stop_no_players(server_id, time_limit):
        can = False
        ttl_no_players = servers_helper.get_TTL_without_player(server_id)
        if (time_limit == -1) or (ttl_no_players > time_limit):
            can = True
        return can

    @staticmethod
    def set_waiting_start(server_id, value):
        try:
            # Checks if server even exists
            Server_Stats.select().where(Server_Stats.server_id == server_id)
        except Exception as ex:
            logger.error(f"Database entry not found! {ex}")
        with database.atomic():
            Server_Stats.update(waiting_start=value).where(Server_Stats.server_id == server_id).execute()

    @staticmethod
    def get_waiting_start(server_id):
        waiting_start = Server_Stats.select().where(Server_Stats.server_id == server_id).get()
        return waiting_start.waiting_start


servers_helper = helper_servers()
