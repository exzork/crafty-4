import logging
import datetime
from peewee import (
    CharField,
    DoesNotExist,
    AutoField,
    DateTimeField,
)
from playhouse.shortcuts import model_to_dict

from app.classes.models.base_model import BaseModel
from app.classes.shared.helpers import Helpers

logger = logging.getLogger(__name__)

# **********************************************************************************
#                                   Roles Class
# **********************************************************************************
class Roles(BaseModel):
    role_id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    last_update = DateTimeField(default=datetime.datetime.now)
    role_name = CharField(default="", unique=True, index=True)

    class Meta:
        table_name = "roles"


# **********************************************************************************
#                                   Roles Helpers
# **********************************************************************************
class helper_roles:
    def __init__(self, database):
        self.database = database

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
        role_id = Roles.insert(
            {
                Roles.role_name: role_name.lower(),
                Roles.created: Helpers.get_time_as_string(),
            }
        ).execute()
        return role_id

    @staticmethod
    def update_role(role_id, up_data):
        return Roles.update(up_data).where(Roles.role_id == role_id).execute()

    def remove_role(self, role_id):
        with self.database.atomic():
            role = Roles.get(Roles.role_id == role_id)
            return role.delete_instance()

    @staticmethod
    def role_id_exists(role_id):
        if not helper_roles.get_role(role_id):
            return False
        return True
