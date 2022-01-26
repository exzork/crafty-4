import sys
import logging
import datetime

from app.classes.shared.helpers import helper
from app.classes.shared.console import console

logger = logging.getLogger(__name__)
peewee_logger = logging.getLogger('peewee')
peewee_logger.setLevel(logging.INFO)

try:
    from peewee import SqliteDatabase, Model, CharField, DoesNotExist, AutoField, DateTimeField
    from playhouse.shortcuts import model_to_dict

except ModuleNotFoundError as e:
    logger.critical(f"Import Error: Unable to load {e.name} module", exc_info=True)
    console.critical(f"Import Error: Unable to load {e.name} module")
    sys.exit(1)

database = SqliteDatabase(helper.db_path, pragmas={
    'journal_mode': 'wal',
    'cache_size': -1024 * 10})

#************************************************************************************************
#                                   Roles Class
#************************************************************************************************
class Roles(Model):
    role_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    last_update = DateTimeField(default=datetime.datetime.now)
    role_name = CharField(default="", unique=True, index=True)

    class Meta:
        table_name = "roles"
        database = database

#************************************************************************************************
#                                   Roles Helpers
#************************************************************************************************
class helper_roles:
    @staticmethod
    def get_all_roles():
        query = Roles.select()
        return query

    @staticmethod
    def get_roleid_by_name(role_name):
        try:
            return (Roles.get(Roles.role_name == role_name)).role_id
        except DoesNotExist:
            return None

    @staticmethod
    def get_role(role_id):
        return model_to_dict(Roles.get(Roles.role_id == role_id))

    @staticmethod
    def add_role(role_name):
        role_id = Roles.insert({
            Roles.role_name: role_name.lower(),
            Roles.created: helper.get_time_as_string()
        }).execute()
        return role_id

    @staticmethod
    def update_role(role_id, up_data):
        return Roles.update(up_data).where(Roles.role_id == role_id).execute()

    @staticmethod
    def remove_role(role_id):
        with database.atomic():
            role = Roles.get(Roles.role_id == role_id)
            return role.delete_instance()

    @staticmethod
    def role_id_exists(role_id):
        if not roles_helper.get_role(role_id):
            return False
        return True

roles_helper = helper_roles()
