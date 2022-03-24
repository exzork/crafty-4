import peewee
import datetime


def migrate(migrator, database, **kwargs):
    db = database

    class Users(peewee.Model):
        user_id = peewee.AutoField()
        created = peewee.DateTimeField(default=datetime.datetime.now)
        last_login = peewee.DateTimeField(default=datetime.datetime.now)
        last_update = peewee.DateTimeField(default=datetime.datetime.now)
        last_ip = peewee.CharField(default="")
        username = peewee.CharField(default="", unique=True, index=True)
        password = peewee.CharField(default="")
        enabled = peewee.BooleanField(default=True)
        superuser = peewee.BooleanField(default=False)
        # we may need to revisit this
        api_token = peewee.CharField(default="", unique=True, index=True)

        class Meta:
            table_name = "users"
            database = db

    class Roles(peewee.Model):
        role_id = peewee.AutoField()
        created = peewee.DateTimeField(default=datetime.datetime.now)
        last_update = peewee.DateTimeField(default=datetime.datetime.now)
        role_name = peewee.CharField(default="", unique=True, index=True)

        class Meta:
            table_name = "roles"
            database = db

    class User_Roles(peewee.Model):
        user_id = peewee.ForeignKeyField(Users, backref="user_role")
        role_id = peewee.ForeignKeyField(Roles, backref="user_role")

        class Meta:
            table_name = "user_roles"
            primary_key = peewee.CompositeKey("user_id", "role_id")
            database = db

    class Audit_Log(peewee.Model):
        audit_id = peewee.AutoField()
        created = peewee.DateTimeField(default=datetime.datetime.now)
        user_name = peewee.CharField(default="")
        user_id = peewee.IntegerField(default=0, index=True)
        source_ip = peewee.CharField(default="127.0.0.1")
        # When auditing global events, use server ID 0
        server_id = peewee.IntegerField(default=None, index=True)
        log_msg = peewee.TextField(default="")

        class Meta:
            database = db

    class Host_Stats(peewee.Model):
        time = peewee.DateTimeField(default=datetime.datetime.now, index=True)
        boot_time = peewee.CharField(default="")
        cpu_usage = peewee.FloatField(default=0)
        cpu_cores = peewee.IntegerField(default=0)
        cpu_cur_freq = peewee.FloatField(default=0)
        cpu_max_freq = peewee.FloatField(default=0)
        mem_percent = peewee.FloatField(default=0)
        mem_usage = peewee.CharField(default="")
        mem_total = peewee.CharField(default="")
        disk_json = peewee.TextField(default="")

        class Meta:
            table_name = "host_stats"
            database = db

    class Servers(peewee.Model):
        server_id = peewee.AutoField()
        created = peewee.DateTimeField(default=datetime.datetime.now)
        server_uuid = peewee.CharField(default="", index=True)
        server_name = peewee.CharField(default="Server", index=True)
        path = peewee.CharField(default="")
        backup_path = peewee.CharField(default="")
        executable = peewee.CharField(default="")
        log_path = peewee.CharField(default="")
        execution_command = peewee.CharField(default="")
        auto_start = peewee.BooleanField(default=0)
        auto_start_delay = peewee.IntegerField(default=10)
        crash_detection = peewee.BooleanField(default=0)
        stop_command = peewee.CharField(default="stop")
        executable_update_url = peewee.CharField(default="")
        server_ip = peewee.CharField(default="127.0.0.1")
        server_port = peewee.IntegerField(default=25565)
        logs_delete_after = peewee.IntegerField(default=0)

        class Meta:
            table_name = "servers"
            database = db

    class User_Servers(peewee.Model):
        user_id = peewee.ForeignKeyField(Users, backref="user_server")
        server_id = peewee.ForeignKeyField(Servers, backref="user_server")

        class Meta:
            table_name = "user_servers"
            primary_key = peewee.CompositeKey("user_id", "server_id")
            database = db

    class Role_Servers(peewee.Model):
        role_id = peewee.ForeignKeyField(Roles, backref="role_server")
        server_id = peewee.ForeignKeyField(Servers, backref="role_server")

        class Meta:
            table_name = "role_servers"
            primary_key = peewee.CompositeKey("role_id", "server_id")
            database = db

    class Server_Stats(peewee.Model):
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

        class Meta:
            table_name = "server_stats"
            database = db

    class Commands(peewee.Model):
        command_id = peewee.AutoField()
        created = peewee.DateTimeField(default=datetime.datetime.now)
        server_id = peewee.ForeignKeyField(Servers, backref="server", index=True)
        user = peewee.ForeignKeyField(Users, backref="user", index=True)
        source_ip = peewee.CharField(default="127.0.0.1")
        command = peewee.CharField(default="")
        executed = peewee.BooleanField(default=False)

        class Meta:
            table_name = "commands"
            database = db

    class Webhooks(peewee.Model):
        id = peewee.AutoField()
        name = peewee.CharField(max_length=64, unique=True, index=True)
        method = peewee.CharField(default="POST")
        url = peewee.CharField(unique=True)
        event = peewee.CharField(default="")
        send_data = peewee.BooleanField(default=True)

        class Meta:
            table_name = "webhooks"
            database = db

    class Schedules(peewee.Model):
        schedule_id = peewee.IntegerField(unique=True, primary_key=True)
        server_id = peewee.ForeignKeyField(Servers, backref="schedule_server")
        enabled = peewee.BooleanField()
        action = peewee.CharField()
        interval = peewee.IntegerField()
        interval_type = peewee.CharField()
        start_time = peewee.CharField(null=True)
        command = peewee.CharField(null=True)
        comment = peewee.CharField()

        class Meta:
            table_name = "schedules"
            database = db

    class Backups(peewee.Model):
        directories = peewee.CharField(null=True)
        max_backups = peewee.IntegerField()
        server_id = peewee.ForeignKeyField(Servers, backref="backups_server")
        schedule_id = peewee.ForeignKeyField(Schedules, backref="backups_schedule")

        class Meta:
            table_name = "backups"
            database = db

    migrator.create_table(Backups)
    migrator.create_table(Users)
    migrator.create_table(Roles)
    migrator.create_table(User_Roles)
    migrator.create_table(User_Servers)
    migrator.create_table(Host_Stats)
    migrator.create_table(Webhooks)
    migrator.create_table(Servers)
    migrator.create_table(Role_Servers)
    migrator.create_table(Server_Stats)
    migrator.create_table(Commands)
    migrator.create_table(Audit_Log)
    migrator.create_table(Schedules)


def rollback(migrator, database, **kwargs):
    migrator.drop_table("users")
    migrator.drop_table("roles")
    migrator.drop_table("user_roles")
    migrator.drop_table(
        "audit_log"
    )  # ? Not 100% sure of the table name, please specify in the schema
    migrator.drop_table("host_stats")
    migrator.drop_table("servers")
    migrator.drop_table("user_servers")
    migrator.drop_table("role_servers")
    migrator.drop_table("server_stats")
    migrator.drop_table("commands")
    migrator.drop_table("webhooks")
    migrator.drop_table("schedules")
    migrator.drop_table("backups")
