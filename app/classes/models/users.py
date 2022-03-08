import logging
import datetime
from typing import Optional, Union

from app.classes.models.roles import Roles, roles_helper
from app.classes.shared.helpers import helper

try:
    from peewee import SqliteDatabase, Model, ForeignKeyField, CharField, AutoField, DateTimeField, BooleanField, CompositeKey, DoesNotExist, JOIN
    from playhouse.shortcuts import model_to_dict

except ModuleNotFoundError as e:
    helper.auto_installer_fix(e)

logger = logging.getLogger(__name__)
peewee_logger = logging.getLogger('peewee')
peewee_logger.setLevel(logging.INFO)
database = SqliteDatabase(helper.db_path, pragmas = {
    'journal_mode': 'wal',
    'cache_size': -1024 * 10})

#************************************************************************************************
#                                   Users Class
#************************************************************************************************
class Users(Model):
    user_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    last_login = DateTimeField(default=datetime.datetime.now)
    last_update = DateTimeField(default=datetime.datetime.now)
    last_ip = CharField(default="")
    username = CharField(default="", unique=True, index=True)
    password = CharField(default="")
    email = CharField(default="default@example.com")
    enabled = BooleanField(default=True)
    superuser = BooleanField(default=False)
    lang = CharField(default="en_EN")
    support_logs = CharField(default = '')
    valid_tokens_from = DateTimeField(default=datetime.datetime.now)
    server_order = CharField(default="")

    class Meta:
        table_name = "users"
        database = database


# ************************************************************************************************
#                                   API Keys Class
# ************************************************************************************************
class ApiKeys(Model):
    token_id = AutoField()
    name = CharField(default='', unique=True, index=True)
    created = DateTimeField(default=datetime.datetime.now)
    user_id = ForeignKeyField(Users, backref='api_token', index=True)
    server_permissions = CharField(default='00000000')
    crafty_permissions = CharField(default='000')
    superuser = BooleanField(default=False)

    class Meta:
        table_name = 'api_keys'
        database = database


#************************************************************************************************
#                                   User Roles Class
#************************************************************************************************
class User_Roles(Model):
    user_id = ForeignKeyField(Users, backref='user_role')
    role_id = ForeignKeyField(Roles, backref='user_role')

    class Meta:
        table_name = 'user_roles'
        primary_key = CompositeKey('user_id', 'role_id')
        database = database

#************************************************************************************************
#                                   Users Helpers
#************************************************************************************************
class helper_users:

    @staticmethod
    def get_by_id(user_id):
        return Users.get_by_id(user_id)

    @staticmethod
    def get_all_users():
        query = Users.select().where(Users.username != "system")
        return query

    @staticmethod
    def get_user_lang_by_id(user_id):
        return Users.get(Users.user_id == user_id).lang

    @staticmethod
    def get_user_id_by_name(username):
        try:
            return (Users.get(Users.username == username)).user_id
        except DoesNotExist:
            return None

    @staticmethod
    def user_query(user_id):
        user_query = Users.select().where(Users.user_id == user_id)
        return user_query

    @staticmethod
    def get_user(user_id):
        if user_id == 0:
            return {
                'user_id': 0,
                'created': '10/24/2019, 11:34:00',
                'last_login': '10/24/2019, 11:34:00',
                'last_update': '10/24/2019, 11:34:00',
                'last_ip': "127.27.23.89",
                'username': "SYSTEM",
                'password': None,
                'email': "default@example.com",
                'enabled': True,
                'superuser': True,
                'roles': [],
                'servers': [],
                'support_logs': '',
            }
        user = model_to_dict(Users.get(Users.user_id == user_id))

        if user:
            # I know it should apply it without setting it but I'm just making sure
            user = users_helper.add_user_roles(user)
            return user
        else:
            #logger.debug("user: ({}) {}".format(user_id, {}))
            return {}

    @staticmethod
    def check_system_user(user_id):
        try:
            result = Users.get(Users.user_id == user_id).user_id == user_id
            if result:
                return True
        except:
            return False

    @staticmethod
    def get_user_model(user_id: str) -> Users:
        user = Users.get(Users.user_id == user_id)
        user = users_helper.add_user_roles(user)
        return user

    @staticmethod
    def add_user(username: str, password: Optional[str] = None, email: Optional[str] = None, enabled: bool = True, superuser: bool = False) -> str:
        if password is not None:
            pw_enc = helper.encode_pass(password)
        else:
            pw_enc = None
        user_id = Users.insert({
            Users.username: username.lower(),
            Users.password: pw_enc,
            Users.email: email,
            Users.enabled: enabled,
            Users.superuser: superuser,
            Users.created: helper.get_time_as_string()
        }).execute()
        return user_id

    @staticmethod
    def update_user(user_id, up_data=None):
        if up_data is None:
            up_data = {}
        if up_data:
            Users.update(up_data).where(Users.user_id == user_id).execute()

    @staticmethod
    def update_server_order(user_id, user_server_order):
        Users.update(server_order = user_server_order).where(Users.user_id == user_id).execute()

    @staticmethod
    def get_server_order(user_id):
        return Users.select().where(Users.user_id == user_id)

    @staticmethod
    def get_super_user_list():
        final_users = []
        # pylint: disable=singleton-comparison
        super_users = Users.select().where(Users.superuser == True)
        for suser in super_users:
            if suser.user_id not in final_users:
                final_users.append(suser.user_id)
        return final_users

    @staticmethod
    def remove_user(user_id):
        with database.atomic():
            User_Roles.delete().where(User_Roles.user_id == user_id).execute()
            user = Users.get(Users.user_id == user_id)
            return user.delete_instance()

    @staticmethod
    def set_support_path(user_id, support_path):
        Users.update(support_logs = support_path).where(Users.user_id == user_id).execute()

    @staticmethod
    def user_id_exists(user_id):
        if not users_helper.get_user(user_id):
            return False
        return True

#************************************************************************************************
#                                   User_Roles Methods
#************************************************************************************************

    @staticmethod
    def get_or_create(user_id, role_id):
        return User_Roles.get_or_create(user_id=user_id, role_id=role_id)

    @staticmethod
    def get_user_roles_id(user_id):
        roles_list = []
        roles = User_Roles.select().where(User_Roles.user_id == user_id)
        for r in roles:
            roles_list.append(roles_helper.get_role(r.role_id)['role_id'])
        return roles_list

    @staticmethod
    def get_user_roles_names(user_id):
        roles_list = []
        roles = User_Roles.select().where(User_Roles.user_id == user_id)
        for r in roles:
            roles_list.append(roles_helper.get_role(r.role_id)['role_name'])
        return roles_list

    @staticmethod
    def add_role_to_user(user_id, role_id):
        User_Roles.insert({
            User_Roles.user_id: user_id,
            User_Roles.role_id: role_id
        }).execute()

    @staticmethod
    def add_user_roles(user: Union[dict, Users]):
        if isinstance(user, dict):
            user_id = user['user_id']
        else:
            user_id = user.user_id

        # I just copied this code from get_user, it had those TODOs & comments made by mac - Lukas

        roles_query = User_Roles.select().join(Roles, JOIN.INNER).where(User_Roles.user_id == user_id)
        # TODO: this query needs to be narrower
        roles = set()
        for r in roles_query:
            roles.add(r.role_id.role_id)

        if isinstance(user, dict):
            user['roles'] = roles
        else:
            user.roles = roles

        #logger.debug("user: ({}) {}".format(user_id, user))
        return user

    @staticmethod
    def user_role_query(user_id):
        user_query = User_Roles.select().where(User_Roles.user_id == user_id)
        query = Roles.select().where(Roles.role_id == -1)
        for u in user_query:
            query = query + Roles.select().where(Roles.role_id == u.role_id)
        return query

    @staticmethod
    def delete_user_roles(user_id, removed_roles):
        User_Roles.delete().where(User_Roles.user_id == user_id).where(User_Roles.role_id.in_(removed_roles)).execute()

    @staticmethod
    def remove_roles_from_role_id(role_id):
        User_Roles.delete().where(User_Roles.role_id == role_id).execute()

# ************************************************************************************************
#                                   ApiKeys Methods
# ************************************************************************************************

    @staticmethod
    def get_user_api_keys(user_id: str):
        return ApiKeys.select().where(ApiKeys.user_id == user_id).execute()

    @staticmethod
    def get_user_api_key(key_id: str) -> ApiKeys:
        return ApiKeys.get(ApiKeys.token_id == key_id)

    @staticmethod
    def add_user_api_key(
         name: str,
         user_id: str,
         superuser: bool = False,
         server_permissions_mask: Optional[str] = None,
         crafty_permissions_mask: Optional[str] = None):
        return ApiKeys.insert({
            ApiKeys.name: name,
            ApiKeys.user_id: user_id,
            **({ApiKeys.server_permissions: server_permissions_mask} if server_permissions_mask is not None else {}),
            **({ApiKeys.crafty_permissions: crafty_permissions_mask} if crafty_permissions_mask is not None else {}),
            ApiKeys.superuser: superuser
        }).execute()

    @staticmethod
    def delete_user_api_keys(user_id: str):
        ApiKeys.delete().where(ApiKeys.user_id == user_id).execute()

    @staticmethod
    def delete_user_api_key(key_id: str):
        ApiKeys.delete().where(ApiKeys.token_id == key_id).execute()



users_helper = helper_users()
