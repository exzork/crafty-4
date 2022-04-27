import os
import logging
import datetime

from app.classes.models.servers import Servers, HelperServers
from app.classes.shared.helpers import Helpers
from app.classes.shared.main_models import DatabaseShortcuts
from app.classes.shared.migration import MigrationManager

try:
    from peewee import (
        SqliteDatabase,
        Model,
        DatabaseProxy,
        ForeignKeyField,
        CharField,
        AutoField,
        DateTimeField,
        BooleanField,
        IntegerField,
        FloatField,
    )

except ModuleNotFoundError as e:
    Helpers.auto_installer_fix(e)

logger = logging.getLogger(__name__)
peewee_logger = logging.getLogger("peewee")
peewee_logger.setLevel(logging.INFO)
database_stats_proxy = DatabaseProxy()


# **********************************************************************************
#                                   Servers Stats Class
# **********************************************************************************
class ServerStats(Model):
    stats_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    server_id = ForeignKeyField(Servers, backref="server", index=True)
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
    downloading = BooleanField(default=False)

    class Meta:
        table_name = "server_stats"
        database = database_stats_proxy


# **********************************************************************************
#                                    Servers_Stats Methods
# **********************************************************************************
class HelperServerStats:
    def __init__(self, database):
        self.database = database

    @staticmethod
    def init_database(server_id):
        try:
            server = HelperServers.get_server_data_by_id(server_id)
            db_folder = os.path.join(f"{server['path']}", "db_stats")
            db_file = os.path.join(
                db_folder,
                f"{server['server_name']}" + ".sqlite",
            )
            database = SqliteDatabase(
                db_file, pragmas={"journal_mode": "wal", "cache_size": -1024 * 10}
            )
            if not os.path.exists(db_file):
                try:
                    os.mkdir(db_folder)
                except Exception as ex:
                    logger.warning(
                        f"Error try to create the db_stats folder for server : {ex}"
                    )
            helper_stats = Helpers()
            helper_stats.migration_dir = os.path.join(
                f"{helper_stats.migration_dir}", "stats"
            )
            helper_stats.db_path = db_file
            database_stats_proxy.initialize(database)
            migration_manager = MigrationManager(database, helper_stats)
            migration_manager.up()  # Automatically runs migrations
            database_stats_proxy.initialize(database)
        except Exception as ex:
            logger.warning(
                f"Error try to look for the db_stats files for server : {ex}"
            )

    @staticmethod
    def select_database(server_id):
        try:
            server = HelperServers.get_server_data_by_id(server_id)
            db_file = os.path.join(
                f"{server['path']}",
                "db_stats",
                f"{server['server_name']}" + ".sqlite",
            )
            database = SqliteDatabase(
                db_file, pragmas={"journal_mode": "wal", "cache_size": -1024 * 10}
            )
            database_stats_proxy.initialize(database)
        except Exception as ex:
            logger.warning(
                f"Error try to look for the db_stats files for server : {ex}"
            )

    @staticmethod
    def get_all_servers_stats():
        servers = HelperServers.get_all_defined_servers()
        server_data = []
        try:
            for s in servers:
                HelperServerStats.select_database(s.get("server_id"))
                latest = (
                    ServerStats.select()
                    .where(ServerStats.server_id == s.get("server_id"))
                    .order_by(ServerStats.created.desc())
                    .limit(1)
                )
                server_data.append(
                    {
                        "server_data": s,
                        "stats": DatabaseShortcuts.return_rows(latest)[0],
                        "user_command_permission": True,
                    }
                )
        except IndexError as ex:
            logger.error(
                f"Stats collection failed with error: {ex}. Was a server just created?"
            )
        return server_data

    @staticmethod
    def insert_server_stats(server):
        server_id = server.get("id", 0)
        HelperServerStats.select_database(server_id)

        if server_id == 0:
            logger.warning("Stats saving failed with error: Server unknown (id = 0)")
            return

        ServerStats.insert(
            {
                ServerStats.server_id: server.get("id", 0),
                ServerStats.started: server.get("started", ""),
                ServerStats.running: server.get("running", False),
                ServerStats.cpu: server.get("cpu", 0),
                ServerStats.mem: server.get("mem", 0),
                ServerStats.mem_percent: server.get("mem_percent", 0),
                ServerStats.world_name: server.get("world_name", ""),
                ServerStats.world_size: server.get("world_size", ""),
                ServerStats.server_port: server.get("server_port", ""),
                ServerStats.int_ping_results: server.get("int_ping_results", False),
                ServerStats.online: server.get("online", False),
                ServerStats.max: server.get("max", False),
                ServerStats.players: server.get("players", False),
                ServerStats.desc: server.get("desc", False),
                ServerStats.version: server.get("version", False),
            }
        ).execute()

    @staticmethod
    def remove_old_stats(server_id, last_week):
        HelperServerStats.select_database(server_id)
        ServerStats.delete().where(ServerStats.created < last_week).execute()

    @staticmethod
    def get_latest_server_stats(server_id):
        HelperServerStats.select_database(server_id)
        return (
            ServerStats.select()
            .where(ServerStats.server_id == server_id)
            .order_by(ServerStats.created.desc())
            .limit(1)
        )

    @staticmethod
    def get_server_stats_by_id(server_id):
        HelperServerStats.select_database(server_id)
        stats = (
            ServerStats.select()
            .where(ServerStats.server_id == server_id)
            .order_by(ServerStats.created.desc())
            .limit(1)
        )
        return DatabaseShortcuts.return_rows(stats)[0]

    @staticmethod
    def server_id_exists(server_id):
        HelperServerStats.select_database(server_id)
        if not HelperServers.get_server_data_by_id(server_id):
            return False
        return True

    @staticmethod
    def sever_crashed(server_id):
        HelperServerStats.select_database(server_id)
        with database_stats_proxy.atomic():
            ServerStats.update(crashed=True).where(
                ServerStats.server_id == server_id
            ).execute()

    @staticmethod
    def set_download(server_id):
        HelperServerStats.select_database(server_id)
        with database_stats_proxy.atomic():
            ServerStats.update(downloading=True).where(
                ServerStats.server_id == server_id
            ).execute()

    @staticmethod
    def finish_download(server_id):
        HelperServerStats.select_database(server_id)
        with database_stats_proxy.atomic():
            ServerStats.update(downloading=False).where(
                ServerStats.server_id == server_id
            ).execute()

    @staticmethod
    def get_download_status(server_id):
        HelperServerStats.select_database(server_id)
        download_status = (
            ServerStats.select().where(ServerStats.server_id == server_id).get()
        )
        return download_status.downloading

    @staticmethod
    def server_crash_reset(server_id):
        if server_id is None:
            return

        HelperServerStats.select_database(server_id)
        with database_stats_proxy.atomic():
            ServerStats.update(crashed=False).where(
                ServerStats.server_id == server_id
            ).execute()

    @staticmethod
    def is_crashed(server_id):
        HelperServerStats.select_database(server_id)
        svr = ServerStats.select().where(ServerStats.server_id == server_id).get()
        # pylint: disable=singleton-comparison
        if svr.crashed == True:
            return True
        else:
            return False

    @staticmethod
    def set_update(server_id, value):
        if server_id is None:
            return

        HelperServerStats.select_database(server_id)
        try:
            # Checks if server even exists
            ServerStats.select().where(ServerStats.server_id == server_id)
        except Exception as ex:
            logger.error(f"Database entry not found! {ex}")
        with database_stats_proxy.atomic():
            ServerStats.update(updating=value).where(
                ServerStats.server_id == server_id
            ).execute()

    @staticmethod
    def get_update_status(server_id):
        HelperServerStats.select_database(server_id)
        update_status = (
            ServerStats.select().where(ServerStats.server_id == server_id).get()
        )
        return update_status.updating

    @staticmethod
    def set_first_run(server_id):
        HelperServerStats.select_database(server_id)
        # Sets first run to false
        try:
            # Checks if server even exists
            ServerStats.select().where(ServerStats.server_id == server_id)
        except Exception as ex:
            logger.error(f"Database entry not found! {ex}")
            return
        with database_stats_proxy.atomic():
            ServerStats.update(first_run=False).where(
                ServerStats.server_id == server_id
            ).execute()

    @staticmethod
    def get_first_run(server_id):
        HelperServerStats.select_database(server_id)
        first_run = ServerStats.select().where(ServerStats.server_id == server_id).get()
        return first_run.first_run

    @staticmethod
    def get_TTL_without_player(server_id):
        HelperServerStats.select_database(server_id)
        last_stat = (
            ServerStats.select()
            .where(ServerStats.server_id == server_id)
            .order_by(ServerStats.created.desc())
            .first()
        )
        last_stat_with_player = (
            ServerStats.select()
            .where(ServerStats.server_id == server_id)
            .where(ServerStats.online > 0)
            .order_by(ServerStats.created.desc())
            .first()
        )
        return last_stat.created - last_stat_with_player.created

    @staticmethod
    def can_stop_no_players(server_id, time_limit):
        HelperServerStats.select_database(server_id)
        can = False
        ttl_no_players = HelperServerStats.get_TTL_without_player(server_id)
        if (time_limit == -1) or (ttl_no_players > time_limit):
            can = True
        return can

    @staticmethod
    def set_waiting_start(server_id, value):
        HelperServerStats.select_database(server_id)
        try:
            # Checks if server even exists
            ServerStats.select().where(ServerStats.server_id == server_id)
        except Exception as ex:
            logger.error(f"Database entry not found! {ex}")
        with database_stats_proxy.atomic():
            ServerStats.update(waiting_start=value).where(
                ServerStats.server_id == server_id
            ).execute()

    @staticmethod
    def get_waiting_start(server_id):
        HelperServerStats.select_database(server_id)
        waiting_start = (
            ServerStats.select().where(ServerStats.server_id == server_id).get()
        )
        return waiting_start.waiting_start
