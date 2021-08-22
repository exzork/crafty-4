import os
import sys
import logging
import datetime

from app.classes.shared.helpers import helper
from app.classes.shared.console import console
from app.classes.minecraft.server_props import ServerProps
from app.classes.web.websocket_helper import websocket_helper

logger = logging.getLogger(__name__)
peewee_logger = logging.getLogger('peewee')
peewee_logger.setLevel(logging.INFO)

try:
    from peewee import *
    from playhouse.shortcuts import model_to_dict
    from enum import Enum
    import yaml

except ModuleNotFoundError as e:
    logger.critical("Import Error: Unable to load {} module".format(e.name), exc_info=True)
    console.critical("Import Error: Unable to load {} module".format(e.name))
    sys.exit(1)

database = SqliteDatabase(helper.db_path, pragmas={
    'journal_mode': 'wal',
    'cache_size': -1024 * 10})


class Users(Model):
    user_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    last_login = DateTimeField(default=datetime.datetime.now)
    last_update = DateTimeField(default=datetime.datetime.now)
    last_ip = CharField(default="")
    username = CharField(default="", unique=True, index=True)
    password = CharField(default="")
    enabled = BooleanField(default=True)
    superuser = BooleanField(default=False)
    api_token = CharField(default="", unique=True, index=True) # we may need to revisit this

    class Meta:
        table_name = "users"
        database = database


class Roles(Model):
    role_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    last_update = DateTimeField(default=datetime.datetime.now)
    role_name = CharField(default="", unique=True, index=True)

    class Meta:
        table_name = "roles"
        database = database


class User_Roles(Model):
    user_id = ForeignKeyField(Users, backref='user_role')
    role_id = ForeignKeyField(Roles, backref='user_role')

    class Meta:
        table_name = 'user_roles'
        primary_key = CompositeKey('user_id', 'role_id')
        database = database


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

    class Meta:
        table_name = "servers"
        database = database

class Role_Servers(Model):
    role_id = ForeignKeyField(Roles, backref='role_server')
    server_id = ForeignKeyField(Servers, backref='role_server')
    permissions = CharField(default="00000000")

    class Meta:
        table_name = 'role_servers'
        primary_key = CompositeKey('role_id', 'server_id')
        database = database

class User_Crafty(Model):
    user_id = ForeignKeyField(Users, backref='users_crafty')
    permissions = CharField(default="00000000")
    limit_server_creation = IntegerField(default=-1)

    class Meta:
        table_name = 'user_crafty'
        database = database

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


    class Meta:
        table_name = "server_stats"
        database = database


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

    class Meta:
        table_name = 'schedules'
        database = database


class Backups(Model):
    directories = CharField(null=True)
    max_backups = IntegerField()
    server_id = ForeignKeyField(Servers, backref='backups_server')
    schedule_id = ForeignKeyField(Schedules, backref='backups_schedule')

    class Meta:
        table_name = 'backups'
        database = database


class db_builder:

    @staticmethod
    def default_settings():
        logger.info("Fresh Install Detected - Creating Default Settings")
        console.info("Fresh Install Detected - Creating Default Settings")
        default_data = helper.find_default_password()

        username = default_data.get("username", 'admin')
        password = default_data.get("password", 'crafty')
        #api_token = helper.random_string_generator(32)
        #
        #Users.insert({
        #    Users.username: username.lower(),
        #    Users.password: helper.encode_pass(password),
        #    Users.api_token: api_token,
        #    Users.enabled: True,
        #    Users.superuser: True
        #}).execute()
        db_shortcuts.add_user(username, password=password, superuser=True)

        #console.info("API token is {}".format(api_token))

    @staticmethod
    def is_fresh_install():
        try:
            user = Users.get_by_id(1)
            return False
        except:
            return True
            pass

class db_shortcuts:

    @staticmethod
    def return_rows(query):
        rows = []

        try:
            if query.count() > 0:
                for s in query:
                    rows.append(model_to_dict(s))
        except Exception as e:
            logger.warning("Database Error: {}".format(e))
            pass

        return rows

    @staticmethod
    def create_server(name: str, server_uuid: str, server_dir: str, backup_path: str, server_command: str, server_file: str, server_log_file: str, server_stop: str, server_port=25565):
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
            Servers.backup_path: backup_path
        }).execute()

    @staticmethod
    def remove_server(server_id):
        with database.atomic():
            Role_Servers.delete().where(Role_Servers.server_id == server_id).execute()
            Servers.delete().where(Servers.server_id == server_id).execute()

    @staticmethod
    def get_server_data_by_id(server_id):
        query = Servers.select().where(Servers.server_id == server_id).limit(1)
        try:
            return db_helper.return_rows(query)[0]
        except IndexError:
            return {}

    @staticmethod
    def get_all_defined_servers():
        query = Servers.select()
        return db_helper.return_rows(query)
        
    @staticmethod
    def get_authorized_servers(user_id):
        server_data = []
        user_roles = User_Roles.select().where(User_Roles.user_id == user_id)
        for us in user_roles:
            role_servers = Role_Servers.select().where(Role_Servers.role_id == us.role_id)
            for role in role_servers:
                server_data.append(db_shortcuts.get_server_data_by_id(role.server_id))

        return server_data

    @staticmethod
    def get_all_servers_stats():
        servers = db_helper.get_all_defined_servers()
        server_data = []

        for s in servers:
            latest = Server_Stats.select().where(Server_Stats.server_id == s.get('server_id')).order_by(Server_Stats.created.desc()).limit(1)
            server_data.append({'server_data': s, "stats": db_helper.return_rows(latest)[0], "user_command_permission":True})
        return server_data

    @staticmethod
    def get_authorized_servers_stats(user_id):
        server_data = []
        authorized_servers = db_helper.get_authorized_servers(user_id)

        for s in authorized_servers:
            latest = Server_Stats.select().where(Server_Stats.server_id == s.get('server_id')).order_by(
                Server_Stats.created.desc()).limit(1)
            user_permissions = db_helper.get_user_permissions_list(user_id, s.get('server_id'))
            if Enum_Permissions_Server.Commands in user_permissions:
                user_command_permission = True
            else:
                user_command_permission = False
            server_data.append({'server_data': s, "stats": db_helper.return_rows(latest)[0], "user_command_permission":user_command_permission})
        return server_data

    @staticmethod
    def get_user_roles_id(user_id):
        roles_list = []
        roles = User_Roles.select().where(User_Roles.user_id == user_id)
        for r in roles:
            roles_list.append(db_helper.get_role(r.role_id)['role_id'])
        return roles_list

    @staticmethod
    def get_user_roles_names(user_id):
        roles_list = []
        roles = User_Roles.select().where(User_Roles.user_id == user_id)
        for r in roles:
            roles_list.append(db_helper.get_role(r.role_id)['role_name'])
        return roles_list

    @staticmethod
    def get_permissions_mask(role_id, server_id):
        permissions_mask = ''
        role_server = Role_Servers.select().where(Role_Servers.role_id == role_id).where(Role_Servers.server_id == server_id).execute()
        permissions_mask = role_server.permissions
        return permissions_mask

    @staticmethod
    def get_role_permissions_list(role_id):
        permissions_mask = ''
        role_server = Role_Servers.select().where(Role_Servers.role_id == role_id).execute()
        permissions_mask = role_server[0].permissions
        permissions_list = server_permissions.get_permissions(permissions_mask)
        return permissions_list

    @staticmethod
    def get_user_permissions_list(user_id, server_id):
        permissions_mask = ''
        permissions_list = []

        user = db_helper.get_user(user_id)
        if user['superuser'] == True:
            permissions_list = server_permissions.get_permissions_list()
        else:
            roles_list = db_helper.get_user_roles_id(user_id)
            role_server = Role_Servers.select().where(Role_Servers.role_id.in_(roles_list)).where(Role_Servers.server_id == int(server_id)).execute()
            permissions_mask = role_server[0].permissions
            permissions_list = server_permissions.get_permissions(permissions_mask)
        return permissions_list

    @staticmethod
    def get_authorized_servers_stats_from_roles(user_id):
        user_roles = User_Roles.select().where(User_Roles.user_id == user_id)
        roles_list = []
        role_server = []
        authorized_servers = []
        server_data = []

        for u in user_roles:
            roles_list.append(db_helper.get_role(u.role_id))
            
        for r in roles_list:
            role_test = Role_Servers.select().where(Role_Servers.role_id == r.get('role_id'))
            for t in role_test:
                role_server.append(t)

        for s in role_server:
            authorized_servers.append(db_helper.get_server_data_by_id(s.server_id))

        for s in authorized_servers:
            latest = Server_Stats.select().where(Server_Stats.server_id == s.get('server_id')).order_by(Server_Stats.created.desc()).limit(1)
            server_data.append({'server_data': s, "stats": db_helper.return_rows(latest)[0]})
        return server_data

    @staticmethod
    def get_server_stats_by_id(server_id):
        stats = Server_Stats.select().where(Server_Stats.server_id == server_id).order_by(Server_Stats.created.desc()).limit(1)
        return db_helper.return_rows(stats)[0]

    @staticmethod
    def server_id_exists(server_id):
        if not db_helper.get_server_data_by_id(server_id):
            return False
        return True
        
    @staticmethod
    def server_id_authorized(serverId, user_id):
        authorized = 0
        user_roles = User_Roles.select().where(User_Roles.user_id == user_id)
        for role in user_roles:
            authorized = (Role_Servers.select().where(Role_Servers.role_id == role.role_id))

        #authorized = db_helper.return_rows(authorized)

        if authorized.count() == 0:
            return False
        return True

    @staticmethod
    def get_latest_hosts_stats():
        query = Host_Stats.select().order_by(Host_Stats.id.desc()).get()
        return model_to_dict(query)

    @staticmethod
    def new_api_token():
        while True:
            token = helper.random_string_generator(32)
            test = list(Users.select(Users.user_id).where(Users.api_token == token))
            if len(test) == 0:
                return token

    @staticmethod
    def get_all_users():
        query = Users.select()
        return query

    @staticmethod
    def get_all_roles():
        query = Roles.select()
        return query

    @staticmethod
    def get_user_id_by_name(username):
        if username == "SYSTEM":
            return 0
        try:
            return (Users.get(Users.username == username)).user_id
        except DoesNotExist:
            return None
    
    @staticmethod
    def get_user_by_api_token(token: str):
        query = Users.select().where(Users.api_token == token)

        if query.exists():
            user = model_to_dict(Users.get(Users.api_token == token))
            # I know it should apply it without setting it but I'm just making sure
            user = db_shortcuts.add_user_roles(user)
            return user
        else:
            return {}
    
    @staticmethod
    def add_role_to_user(user_id, role_id):
        User_Roles.insert({
            User_Roles.user_id: user_id,
            User_Roles.role_id: role_id
        }).execute()

    @staticmethod
    def add_user_roles(user):
        if type(user) == dict:
            user_id = user['user_id']
        else:
            user_id = user.user_id

        # I just copied this code from get_user, it had those TODOs & comments made by mac - Lukas
        
        roles_query = User_Roles.select().join(Roles, JOIN.INNER).where(User_Roles.user_id == user_id)
        # TODO: this query needs to be narrower
        roles = set()
        for r in roles_query:
            roles.add(r.role_id.role_id)

        user['roles'] = roles
        #logger.debug("user: ({}) {}".format(user_id, user))
        return user

    @staticmethod
    def add_user_crafty(user_id, uc_permissions):
        user_crafty = User_Crafty.insert({User_Crafty.user_id: user_id, User_Crafty.permissions: uc_permissions}).execute()
        return user_crafty

    @staticmethod
    def add_role_server(server_id, role_id, rs_permissions="00000000"):
        servers = Role_Servers.insert({Role_Servers.server_id: server_id, Role_Servers.role_id: role_id, Role_Servers.permissions: rs_permissions}).execute()
        return servers


    @staticmethod
    def user_query(user_id):
        user_query = Users.select().where(Users.user_id == user_id)
        return user_query

    @staticmethod
    def user_role_query(user_id):
        user_query = User_Roles.select().where(User_Roles.user_id == user_id)
        query = Roles.select().where(Roles.role_id == -1)
        for u in user_query:
            query = Roles.select().where(Roles.role_id == u.role_id)
        return query

    @staticmethod
    def get_user(user_id):
        if user_id == 0:
            return {
                'user_id': 0,
                'created': None,
                'last_login': None,
                'last_update': None,
                'last_ip': "127.27.23.89",
                'username': "SYSTEM",
                'password': None,
                'enabled': True,
                'superuser': False,
                'api_token': None,
                'roles': [],
                'servers': [],
            }
        user = model_to_dict(Users.get(Users.user_id == user_id))

        if user:
            # I know it should apply it without setting it but I'm just making sure
            user = db_shortcuts.add_user_roles(user)
            return user
        else:
            #logger.debug("user: ({}) {}".format(user_id, {}))
            return {}

    @staticmethod
    def update_user(user_id, user_data={}):
        base_data = db_helper.get_user(user_id)
        up_data = {}
        added_roles = set()
        removed_roles = set()
        removed_servers = set()
        for key in user_data:
            if key == "user_id":
                continue
            elif key == "roles":
                added_roles = user_data['roles'].difference(base_data['roles'])
                removed_roles = base_data['roles'].difference(user_data['roles'])
            elif key == "regen_api":
                if user_data['regen_api']:
                    up_data['api_token'] = db_shortcuts.new_api_token()
            elif key == "password":
                if user_data['password'] is not None and user_data['password'] != "":
                    up_data['password'] = helper.encode_pass(user_data['password'])
            elif base_data[key] != user_data[key]:
                up_data[key] = user_data[key]
        up_data['last_update'] = helper.get_time_as_string()
        logger.debug("user: {} +role:{} -role:{}".format(user_data, added_roles, removed_roles))
        with database.atomic():
            for role in added_roles:
                User_Roles.get_or_create(user_id=user_id, role_id=role)
                # TODO: This is horribly inefficient and we should be using bulk queries but im going for functionality at this point
            User_Roles.delete().where(User_Roles.user_id == user_id).where(User_Roles.role_id.in_(removed_roles)).execute()

            if up_data:
                Users.update(up_data).where(Users.user_id == user_id).execute()

    @staticmethod
    def add_user(username, password=None, api_token=None, enabled=True, superuser=False):
        if password is not None:
            pw_enc = helper.encode_pass(password)
        else:
            pw_enc = None
        if api_token is None:
            api_token = db_shortcuts.new_api_token()
        else:
            if type(api_token) is not str and len(api_token) != 32:
                raise ValueError("API token must be a 32 character string")
        user_id = Users.insert({
            Users.username: username.lower(),
            Users.password: pw_enc,
            Users.api_token: api_token,
            Users.enabled: enabled,
            Users.superuser: superuser,
            Users.created: helper.get_time_as_string()
        }).execute()
        return user_id

    @staticmethod
    def remove_user(user_id):
        with database.atomic():
            User_Roles.delete().where(User_Roles.user_id == user_id).execute()
            user = Users.get(Users.user_id == user_id)
            return user.delete_instance()

    @staticmethod
    def user_id_exists(user_id):
        if not db_shortcuts.get_user(user_id):
            return False
        return True

    @staticmethod
    def get_roleid_by_name(role_name):
        try:
            return (Roles.get(Roles.role_name == role_name)).role_id
        except DoesNotExist:
            return None

    @staticmethod
    def get_role(role_id):
        role = model_to_dict(Roles.get(Roles.role_id == role_id))

        if role:
            servers_query = Role_Servers.select().join(Servers, JOIN.INNER).where(Role_Servers.role_id == role_id)
            # TODO: this query needs to be narrower
            servers = set()
            for s in servers_query:
                servers.add(s.server_id.server_id)
            role['servers'] = servers
            #logger.debug("role: ({}) {}".format(role_id, role))
            return role
        else:
            #logger.debug("role: ({}) {}".format(role_id, {}))
            return {}

    @staticmethod
    def update_role(role_id, role_data={}, permissions_mask="00000000"):
        base_data = db_helper.get_role(role_id)
        up_data = {}
        added_servers = set()
        edited_servers = set()
        removed_servers = set()
        for key in role_data:
            if key == "role_id":
                continue
            elif key == "servers":
                added_servers = role_data['servers'].difference(base_data['servers'])
                removed_servers = base_data['servers'].difference(role_data['servers'])
            elif base_data[key] != role_data[key]:
                up_data[key] = role_data[key]
        up_data['last_update'] = helper.get_time_as_string()
        logger.debug("role: {} +server:{} -server{}".format(role_data, added_servers, removed_servers))
        with database.atomic():
            for server in added_servers:
                Role_Servers.get_or_create(role_id=role_id, server_id=server, permissions=permissions_mask)
            for server in base_data['servers']:
                role_server = Role_Servers.select().where(Role_Servers.role_id == role_id).where(Role_Servers.server_id == server).get()
                role_server.permissions = permissions_mask
                Role_Servers.save(role_server)
                # TODO: This is horribly inefficient and we should be using bulk queries but im going for functionality at this point
            Role_Servers.delete().where(Role_Servers.role_id == role_id).where(Role_Servers.server_id.in_(removed_servers)).execute()
            if up_data:
                Roles.update(up_data).where(Roles.role_id == role_id).execute()

    @staticmethod
    def add_role(role_name):
        role_id = Roles.insert({
            Roles.role_name: role_name.lower(),
            Roles.created: helper.get_time_as_string()
        }).execute()
        return role_id

    @staticmethod
    def remove_role(role_id):
        with database.atomic():
            Role_Servers.delete().where(Role_Servers.role_id == role_id).execute()
            User_Roles.delete().where(User_Roles.role_id == role_id).execute()
            role = Roles.get(Roles.role_id == role_id)
            return role.delete_instance()

    @staticmethod
    def role_id_exists(role_id):
        if not db_shortcuts.get_role(role_id):
            return False
        return True

    @staticmethod
    def get_unactioned_commands():
        query = Commands.select().where(Commands.executed == 0)
        return db_helper.return_rows(query)

    @staticmethod
    def get_server_friendly_name(server_id):
        server_data = db_helper.get_server_data_by_id(server_id)
        friendly_name = "{} with ID: {}".format(server_data.get('server_name', None), server_data.get('server_id', 0))
        return friendly_name

    @staticmethod
    def send_command(user_id, server_id, remote_ip, command):

        server_name = db_helper.get_server_friendly_name(server_id)

        # Example: Admin issued command start_server for server Survival
        db_helper.add_to_audit_log(user_id, "issued command {} for server {}".format(command, server_name),
                              server_id, remote_ip)

        Commands.insert({
            Commands.server_id: server_id,
            Commands.user: user_id,
            Commands.source_ip: remote_ip,
            Commands.command: command
        }).execute()

    @staticmethod
    def get_actity_log():
        q = Audit_Log.select()
        return db_helper.return_db_rows(q)

    @staticmethod
    def return_db_rows(model):
        data = [model_to_dict(row) for row in model]
        return data

    @staticmethod
    def mark_command_complete(command_id=None):
        if command_id is not None:
            logger.debug("Marking Command {} completed".format(command_id))
            Commands.update({
                Commands.executed: True
            }).where(Commands.command_id == command_id).execute()

    def add_to_audit_log(self, user_id, log_msg, server_id=None, source_ip=None):
        logger.debug("Adding to audit log User:{} - Message: {} ".format(user_id, log_msg))
        user_data = self.get_user(user_id)

        audit_msg = "{} {}".format(str(user_data['username']).capitalize(), log_msg)

        websocket_helper.broadcast('notification', audit_msg)

        Audit_Log.insert({
            Audit_Log.user_name: user_data['username'],
            Audit_Log.user_id: user_id,
            Audit_Log.server_id: server_id,
            Audit_Log.log_msg: audit_msg,
            Audit_Log.source_ip: source_ip
        }).execute()
    
    @staticmethod
    def add_to_audit_log_raw(user_name, user_id, server_id, log_msg, source_ip):
        Audit_Log.insert({
            Audit_Log.user_name: user_name,
            Audit_Log.user_id: user_id,
            Audit_Log.server_id: server_id,
            Audit_Log.log_msg: log_msg,
            Audit_Log.source_ip: source_ip
        }).execute()

    @staticmethod
    def create_scheduled_task(server_id, action, interval, interval_type, start_time, command, comment=None, enabled=True):
        sch_id = Schedules.insert({
            Schedules.server_id: server_id,
            Schedules.action: action,
            Schedules.enabled: enabled,
            Schedules.interval: interval,
            Schedules.interval_type: interval_type,
            Schedules.start_time: start_time,
            Schedules.command: command,
            Schedules.comment: comment
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
    def get_scheduled_task(schedule_id):
        return model_to_dict(Schedules.get(Schedules.schedule_id == schedule_id)).execute()

    @staticmethod
    def get_schedules_by_server(server_id):
        return Schedules.select().where(Schedules.server_id == server_id).execute()

    @staticmethod
    def get_schedules_all():
        return Schedules.select().execute()

    @staticmethod
    def get_schedules_enabled():
        return Schedules.select().where(Schedules.enabled == True).execute()

    @staticmethod
    def get_backup_config(server_id):
        try:
            row = Backups.select().where(Backups.server_id == server_id).join(Schedules).join(Servers)[0]
            conf = {
                "backup_path": row.server_id.backup_path,
                "directories": row.directories,
                "max_backups": row.max_backups,
                "auto_enabled": row.schedule_id.enabled,
                "server_id": row.server_id.server_id
            }
        except IndexError:
            conf = {
                "backup_path": None,
                "directories": None,
                "max_backups": 0,
                "auto_enabled": True,
                "server_id": server_id
            }
        return conf

    @staticmethod
    def set_update(server_id, value):
        try:
            row = Server_Stats.select().where(Server_Stats.server_id == server_id)
        except Exception as ex:
            logger.error("Database entry not found. ".format(ex))
        with database.atomic():
            Server_Stats.update(updating=value).where(Server_Stats.server_id == server_id).execute()

    @staticmethod
    def set_backup_config(server_id: int, backup_path: str = None, max_backups: int = None, auto_enabled: bool = True):
        logger.debug("Updating server {} backup config with {}".format(server_id, locals()))
        try:
            row = Backups.select().where(Backups.server_id == server_id).join(Schedules).join(Servers)[0]
            new_row = False
            conf = {}
            schd = {}
        except IndexError:
            conf = {
                "directories": None,
                "max_backups": 0,
                "server_id":   server_id
            }
            schd = {
                "enabled":    True,
                "action":     "backup_server",
                "interval_type": "days",
                "interval":   1,
                "start_time": "00:00",
                "server_id":  server_id,
                "comment":    "Default backup job"
            }
            new_row = True
        if max_backups is not None:
            conf['max_backups'] = max_backups
        schd['enabled'] = bool(auto_enabled)
        if not new_row:
            with database.atomic():
                if backup_path is not None:
                    u1 = Servers.update(backup_path=backup_path).where(Servers.server_id == server_id).execute()
                else:
                    u1 = 0
                u2 = Backups.update(conf).where(Backups.server_id == server_id).execute()
                u3 = Schedules.update(schd).where(Schedules.schedule_id == row.schedule_id).execute()
            logger.debug("Updating existing backup record.  {}+{}+{} rows affected".format(u1, u2, u3))
        else:
            with database.atomic():
                conf["server_id"] = server_id
                if backup_path is not None:
                    u = Servers.update(backup_path=backup_path).where(Servers.server_id == server_id)
                s = Schedules.create(**schd)
                conf['schedule_id'] = s.schedule_id
                b = Backups.create(**conf)
            logger.debug("Creating new backup record.")

class Enum_Permissions_Server(Enum):
    Commands = 0
    Terminal = 1
    Logs = 2
    Schedule = 3
    Backup = 4
    Files = 5
    Config = 6
    Players = 7

class Permissions_Servers:

    @staticmethod
    def get_permissions_list():
        permissions_list = []
        for member in Enum_Permissions_Server.__members__.items():
            permissions_list.append(member[1])
        return permissions_list
        
    @staticmethod
    def get_permissions(permissions_mask):
        permissions_list = []
        for member in Enum_Permissions_Server.__members__.items():
            if server_permissions.has_permission(permissions_mask, member[1]):
                permissions_list.append(member[1])
        return permissions_list

    @staticmethod
    def has_permission(permission_mask, permission_tested: Enum_Permissions_Server):
        result = False
        if permission_mask[permission_tested.value] == '1':
            result = True
        return result
        
    @staticmethod
    def set_permission(permission_mask, permission_tested: Enum_Permissions_Server, value):
        l = list(permission_mask)
        l[permission_tested.value] = str(value)
        permission_mask = ''.join(l)
        return permission_mask
        
    @staticmethod
    def get_permission(permission_mask, permission_tested: Enum_Permissions_Server):
        return permission_mask[permission_tested.value]    

class Enum_Permissions_Crafty(Enum):
    Server_Creation = 0
    User_Config = 1
    Roles_Config = 2
    
class Permissions_Crafty:

    @staticmethod
    def get_permissions_list():
        permissions_list = []
        for member in Enum_Permissions_Crafty.__members__.items():
            permissions_list.append(member[1])
        return permissions_list
        
    @staticmethod
    def get_permissions(permissions_mask):
        permissions_list = []
        for member in Enum_Permissions_Crafty.__members__.items():
            if server_permissions.has_permission(permissions_mask, member[1]):
                permissions_list.append(member[1])
        return permissions_list

    @staticmethod
    def has_permission(permission_mask, permission_tested: Enum_Permissions_Crafty):
        result = False
        if permission_mask[permission_tested.value] == '1':
            result = True
        return result
        
    @staticmethod
    def set_permission(permission_mask, permission_tested: Enum_Permissions_Crafty, value):
        l = list(permission_mask)
        l[permission_tested.value] = str(value)
        permission_mask = ''.join(l)
        return permission_mask
        
    @staticmethod
    def get_permission(permission_mask, permission_tested: Enum_Permissions_Crafty):
        return permission_mask[permission_tested.value]  

installer = db_builder()
db_helper = db_shortcuts()
server_permissions = Permissions_Servers()
crafty_permissions = Permissions_Crafty()