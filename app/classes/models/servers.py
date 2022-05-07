import logging
import datetime
import typing as t
from peewee import (
    ForeignKeyField,
    CharField,
    AutoField,
    DateTimeField,
    BooleanField,
    IntegerField,
    FloatField,
)
from playhouse.shortcuts import model_to_dict

from app.classes.shared.main_models import DatabaseShortcuts
from app.classes.models.base_model import BaseModel

logger = logging.getLogger(__name__)

# **********************************************************************************
#                                   Servers Class
# **********************************************************************************
class Servers(BaseModel):
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


# **********************************************************************************
#                                   Servers Stats Class
# **********************************************************************************
class ServerStats(BaseModel):
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
#                                   Servers Class
# **********************************************************************************
class HelperServers:
    def __init__(self, database):
        self.database = database

    # **********************************************************************************
    #                                   Generic Servers Methods
    # **********************************************************************************
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
        server_port: int = 25565,
        server_host: str = "127.0.0.1",
    ) -> int:
        """Create a server in the database

        Args:
            name: The name of the server
            server_uuid: This is the UUID of the server
            server_dir: The directory where the server is located
            backup_path: The path to the backup folder
            server_command: The command to start the server
            server_file: The name of the server file
            server_log_file: The path to the server log file
            server_stop: This is the command to stop the server
            server_type: This is the type of server you're creating.
            server_port: The port the server will be monitored on, defaults to 25565
            server_host: The host the server will be monitored on, defaults to 127.0.0.1

        Returns:
            int: The new server's id

        Raises:
            PeeweeException: If the server already exists
        """
        return Servers.insert(
            {
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
                Servers.server_ip: server_host,
                Servers.stop_command: server_stop,
                Servers.backup_path: backup_path,
                Servers.type: server_type,
            }
        ).execute()

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

    def remove_server(self, server_id):
        with self.database.atomic():
            Servers.delete().where(Servers.server_id == server_id).execute()

    @staticmethod
    def get_server_data_by_id(server_id):
        query = Servers.select().where(Servers.server_id == server_id).limit(1)
        try:
            return DatabaseShortcuts.return_rows(query)[0]
        except IndexError:
            return {}

    @staticmethod
    def get_server_columns(
        server_id: t.Union[str, int], column_names: t.List[str]
    ) -> t.List[t.Any]:
        columns = [getattr(Servers, column) for column in column_names]
        return model_to_dict(
            Servers.select(*columns).where(Servers.server_id == server_id).get(),
            only=columns,
        )

    @staticmethod
    def get_server_column(server_id: t.Union[str, int], column_name: str) -> t.Any:
        column = getattr(Servers, column_name)
        return model_to_dict(
            Servers.select(column).where(Servers.server_id == server_id).get(),
            only=[column],
        )[column_name]

    # **********************************************************************************
    #                                     Servers Methods
    # **********************************************************************************
    @staticmethod
    def get_all_defined_servers():
        query = Servers.select()
        return DatabaseShortcuts.return_rows(query)

    @staticmethod
    def get_all_servers_stats():
        servers = HelperServers.get_all_defined_servers()
        server_data = []
        try:
            for s in servers:
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
    def get_server_friendly_name(server_id):
        server_data = HelperServers.get_server_data_by_id(server_id)
        friendly_name = (
            f"{server_data.get('server_name', None)} "
            f"with ID: {server_data.get('server_id', 0)}"
        )
        return friendly_name

    # **********************************************************************************
    #                                    Servers_Stats Methods
    # **********************************************************************************
    @staticmethod
    def get_latest_server_stats(server_id):
        return (
            ServerStats.select()
            .where(ServerStats.server_id == server_id)
            .order_by(ServerStats.created.desc())
            .limit(1)
        )

    @staticmethod
    def get_server_stats_by_id(server_id):
        stats = (
            ServerStats.select()
            .where(ServerStats.server_id == server_id)
            .order_by(ServerStats.created.desc())
            .limit(1)
        )
        return DatabaseShortcuts.return_rows(stats)[0]

    @staticmethod
    def server_id_exists(server_id):
        if not HelperServers.get_server_data_by_id(server_id):
            return False
        return True

    @staticmethod
    def sever_crashed(server_id):
        ServerStats.update(crashed=True).where(
            ServerStats.server_id == server_id
        ).execute()

    @staticmethod
    def set_download(server_id):
        ServerStats.update(downloading=True).where(
            ServerStats.server_id == server_id
        ).execute()

    @staticmethod
    def finish_download(server_id):
        ServerStats.update(downloading=False).where(
            ServerStats.server_id == server_id
        ).execute()

    @staticmethod
    def get_download_status(server_id):
        download_status = (
            ServerStats.select().where(ServerStats.server_id == server_id).get()
        )
        return download_status.downloading

    @staticmethod
    def server_crash_reset(server_id):
        ServerStats.update(crashed=False).where(
            ServerStats.server_id == server_id
        ).execute()

    @staticmethod
    def is_crashed(server_id):
        svr = ServerStats.select().where(ServerStats.server_id == server_id).get()
        if svr.crashed is True:
            return True
        else:
            return False

    @staticmethod
    def set_update(server_id, value):
        try:
            # Checks if server even exists
            ServerStats.select().where(ServerStats.server_id == server_id)
        except Exception as ex:
            logger.error(f"Database entry not found! {ex}")
        ServerStats.update(updating=value).where(
            ServerStats.server_id == server_id
        ).execute()

    @staticmethod
    def get_update_status(server_id):
        update_status = (
            ServerStats.select().where(ServerStats.server_id == server_id).get()
        )
        return update_status.updating

    @staticmethod
    def set_first_run(server_id):
        # Sets first run to false
        try:
            # Checks if server even exists
            ServerStats.select().where(ServerStats.server_id == server_id)
        except Exception as ex:
            logger.error(f"Database entry not found! {ex}")
            return
        ServerStats.update(first_run=False).where(
            ServerStats.server_id == server_id
        ).execute()

    @staticmethod
    def get_first_run(server_id):
        first_run = ServerStats.select().where(ServerStats.server_id == server_id).get()
        return first_run.first_run

    @staticmethod
    def get_ttl_without_player(server_id):
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
        can = False
        ttl_no_players = HelperServers.get_ttl_without_player(server_id)
        if (time_limit == -1) or (ttl_no_players > time_limit):
            can = True
        return can

    @staticmethod
    def set_waiting_start(server_id, value):
        try:
            # Checks if server even exists
            ServerStats.select().where(ServerStats.server_id == server_id)
        except Exception as ex:
            logger.error(f"Database entry not found! {ex}")
        ServerStats.update(waiting_start=value).where(
            ServerStats.server_id == server_id
        ).execute()

    @staticmethod
    def get_waiting_start(server_id):
        waiting_start = (
            ServerStats.select().where(ServerStats.server_id == server_id).get()
        )
        return waiting_start.waiting_start
