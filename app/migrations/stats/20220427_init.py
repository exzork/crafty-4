import peewee
import datetime

from app.classes.models.servers import Servers


def migrate(migrator, database, **kwargs):
    db = database

    class ServerStats(peewee.Model):
        stats_id = peewee.AutoField()
        created = peewee.DateTimeField(default=datetime.datetime.now)
        server_id = peewee.ForeignKeyField(Servers, backref="server", index=True)
        started = peewee.CharField(default="")
        running = peewee.BooleanField(default=False)
        cpu = peewee.FloatField(default=0)
        mem = peewee.FloatField(default=0)
        mem_percent = peewee.FloatField(default=0)
        world_name = peewee.CharField(default="")
        world_size = peewee.CharField(default="")
        server_port = peewee.IntegerField(default=25565)
        int_ping_results = peewee.CharField(default="")
        online = peewee.IntegerField(default=0)
        max = peewee.IntegerField(default=0)
        players = peewee.CharField(default="")
        desc = peewee.CharField(default="Unable to Connect")
        version = peewee.CharField(default="")
        updating = peewee.BooleanField(default=False)
        waiting_start = peewee.BooleanField(default=False)
        first_run = peewee.BooleanField(default=True)
        crashed = peewee.BooleanField(default=False)
        downloading = peewee.BooleanField(default=False)

        class Meta:
            table_name = "server_stats"
            database = db

    migrator.create_table(ServerStats)


def rollback(migrator, database, **kwargs):
    migrator.drop_table("server_stats")
