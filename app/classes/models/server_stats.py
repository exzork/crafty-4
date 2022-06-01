import os
import logging
import datetime
import typing as t

from playhouse.shortcuts import model_to_dict

from app.classes.models.servers import Servers, HelperServers
from app.classes.shared.helpers import Helpers
from app.classes.shared.migration import MigrationManager

try:
    from peewee import (
        SqliteDatabase,
        Model,
        ForeignKeyField,
        CharField,
        AutoField,
        DateTimeField,
        BooleanField,
        IntegerField,
        FloatField,
        DoesNotExist,
    )

except ModuleNotFoundError as e:
    Helpers.auto_installer_fix(e)

logger = logging.getLogger(__name__)
peewee_logger = logging.getLogger("peewee")
peewee_logger.setLevel(logging.INFO)


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


# **********************************************************************************
#                                    Servers_Stats Methods
# **********************************************************************************
class HelperServerStats:
    def __init__(self, database):
        self.database = database

    @staticmethod
    def init_database(server_id) -> t.Optional[SqliteDatabase]:
        try:
            server = HelperServers.get_server_data_by_id(server_id)
            db_folder = os.path.join(f"{server['path']}", "db_stats")
            db_file = os.path.join(
                db_folder,
                "crafty_server_stats.sqlite",
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
            migration_manager = MigrationManager(database, helper_stats)
            migration_manager.up()  # Automatically runs migrations
            return database
        except Exception as ex:
            logger.warning(
                f"Error try to look for the db_stats files for server : {ex}"
            )
            return None

    @staticmethod
    def select_database(server_id) -> t.Optional[SqliteDatabase]:
        try:
            server = HelperServers.get_server_data_by_id(server_id)
            db_file = os.path.join(
                f"{server['path']}",
                "db_stats",
                "crafty_server_stats.sqlite",
            )
            database = SqliteDatabase(
                db_file, pragmas={"journal_mode": "wal", "cache_size": -1024 * 10}
            )
            return database
        except Exception as ex:
            logger.warning(
                f"Error try to look for the db_stats files for server : {ex}"
            )
            return None

    @staticmethod
    def get_all_servers_stats():
        servers = HelperServers.get_all_defined_servers()
        server_data = []
        try:
            for server in servers:
                stats = HelperServerStats.get_server_stats_by_id(server["server_id"])

                server_data.append(
                    {
                        "server_data": server,
                        "stats": stats,
                        "user_command_permission": True,
                    }
                )
        except IndexError as ex:
            logger.error(
                f"Stats collection failed with error: {ex}. Was a server just created?"
            )
        return server_data

    @staticmethod
    def insert_server_stats(server_stats):
        server_id = server_stats.get("id", 0)
        database = HelperServerStats.select_database(server_id)

        if server_id == 0:
            logger.warning("Stats saving failed with error: Server unknown (id = 0)")
            return

        ServerStats.insert(
            {
                ServerStats.server_id: server_stats.get("id", 0),
                ServerStats.started: server_stats.get("started", ""),
                ServerStats.running: server_stats.get("running", False),
                ServerStats.cpu: server_stats.get("cpu", 0),
                ServerStats.mem: server_stats.get("mem", 0),
                ServerStats.mem_percent: server_stats.get("mem_percent", 0),
                ServerStats.world_name: server_stats.get("world_name", ""),
                ServerStats.world_size: server_stats.get("world_size", ""),
                ServerStats.server_port: server_stats.get("server_port", 0),
                ServerStats.int_ping_results: server_stats.get(
                    "int_ping_results", False
                ),
                ServerStats.online: server_stats.get("online", False),
                ServerStats.max: server_stats.get("max", False),
                ServerStats.players: server_stats.get("players", False),
                ServerStats.desc: server_stats.get("desc", False),
                ServerStats.version: server_stats.get("version", False),
            }
        ).execute(database)

    @staticmethod
    def remove_old_stats(server_id, minimum_to_exist):
        database = HelperServerStats.select_database(server_id)
        ServerStats.delete().where(ServerStats.created < minimum_to_exist).execute(
            database
        )

    @staticmethod
    def get_latest_server_stats(server_id):
        database = HelperServerStats.select_database(server_id)
        return (
            ServerStats.select()
            .where(ServerStats.server_id == server_id)
            .order_by(ServerStats.created.desc())
            .limit(1)
            .execute(database)
        )

    @staticmethod
    def get_server_stats_by_id(server_id):
        database = HelperServerStats.select_database(server_id)
        stats = (
            ServerStats.select()
            .where(ServerStats.server_id == server_id)
            .order_by(ServerStats.created.desc())
            .limit(1)
            .first(database)
        )
        return model_to_dict(stats)

    @staticmethod
    def server_id_exists(server_id):
        database = HelperServerStats.select_database(server_id)
        # We can't use .exists because it doesn't seem to use the database parameter
        return (
            ServerStats.select()
            .where(ServerStats.server_id == server_id)
            .count(database)
            != 0
        )

    @staticmethod
    def sever_crashed(server_id):
        database = HelperServerStats.select_database(server_id)
        ServerStats.update(crashed=True).where(
            ServerStats.server_id == server_id
        ).execute(database)

    @staticmethod
    def set_download(server_id):
        database = HelperServerStats.select_database(server_id)
        ServerStats.update(downloading=True).where(
            ServerStats.server_id == server_id
        ).execute(database)

    @staticmethod
    def finish_download(server_id):
        database = HelperServerStats.select_database(server_id)
        ServerStats.update(downloading=False).where(
            ServerStats.server_id == server_id
        ).execute(database)

    @staticmethod
    def get_download_status(server_id):
        database = HelperServerStats.select_database(server_id)
        download_status = (
            ServerStats.select().where(ServerStats.server_id == server_id).get(database)
        )
        return download_status.downloading

    @staticmethod
    def server_crash_reset(server_id):
        if server_id is None:
            return

        database = HelperServerStats.select_database(server_id)
        ServerStats.update(crashed=False).where(
            ServerStats.server_id == server_id
        ).execute(database)

    @staticmethod
    def is_crashed(server_id):
        database = HelperServerStats.select_database(server_id)
        svr = (
            ServerStats.select().where(ServerStats.server_id == server_id).get(database)
        )
        return svr.crashed

    @staticmethod
    def set_update(server_id, value):
        if server_id is None:
            return

        database = HelperServerStats.select_database(server_id)
        try:
            # Checks if server even exists
            ServerStats.select().where(ServerStats.server_id == server_id).execute(
                database
            )
        except DoesNotExist as ex:
            logger.error(f"Database entry not found! {ex}")
            return
        ServerStats.update(updating=value).where(
            ServerStats.server_id == server_id
        ).execute(database)

    @staticmethod
    def get_update_status(server_id):
        database = HelperServerStats.select_database(server_id)
        update_status = (
            ServerStats.select().where(ServerStats.server_id == server_id).get(database)
        )
        return update_status.updating

    @staticmethod
    def set_first_run(server_id):
        database = HelperServerStats.select_database(server_id)
        # Sets first run to false
        try:
            # Checks if server even exists
            ServerStats.select().where(ServerStats.server_id == server_id)
        except DoesNotExist as ex:
            logger.error(f"Database entry not found! {ex}")
            return
        ServerStats.update(first_run=False).where(
            ServerStats.server_id == server_id
        ).execute(database)

    @staticmethod
    def get_first_run(server_id):
        database = HelperServerStats.select_database(server_id)
        first_run = (
            ServerStats.select().where(ServerStats.server_id == server_id).get(database)
        )
        return first_run.first_run

    @staticmethod
    def get_ttl_without_player(server_id):
        database = HelperServerStats.select_database(server_id)
        last_stat = (
            ServerStats.select()
            .where(ServerStats.server_id == server_id)
            .order_by(ServerStats.created.desc())
            .first(database)
        )
        last_stat_with_player = (
            ServerStats.select()
            .where(ServerStats.server_id == server_id)
            .where(ServerStats.online > 0)
            .order_by(ServerStats.created.desc())
            .first(database)
        )
        return last_stat.created - last_stat_with_player.created

    @staticmethod
    def can_stop_no_players(server_id, time_limit):
        ttl_no_players = HelperServerStats.get_ttl_without_player(server_id)
        return (time_limit == -1) or (ttl_no_players > time_limit)

    @staticmethod
    def set_waiting_start(server_id, value):
        database = HelperServerStats.select_database(server_id)
        try:
            # Checks if server even exists
            ServerStats.select().where(ServerStats.server_id == server_id).execute(
                database
            )
        except DoesNotExist as ex:
            logger.error(f"Database entry not found! {ex}")
            return
        ServerStats.update(waiting_start=value).where(
            ServerStats.server_id == server_id
        ).execute(database)

    @staticmethod
    def get_waiting_start(server_id):
        database = HelperServerStats.select_database(server_id)
        waiting_start = (
            ServerStats.select().where(ServerStats.server_id == server_id).get(database)
        )
        return waiting_start.waiting_start
