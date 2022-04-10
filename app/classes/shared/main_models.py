import logging

from app.classes.models.users import Users, users_helper
from app.classes.shared.helpers import helper
from app.classes.shared.console import console

# To disable warning about unused import ; Users is imported from here in other places
# pylint: disable=self-assigning-variable
Users = Users

try:
    # pylint: disable=unused-import
    from peewee import SqliteDatabase, fn
    from playhouse.shortcuts import model_to_dict

except ModuleNotFoundError as err:
    helper.auto_installer_fix(err)

logger = logging.getLogger(__name__)
peewee_logger = logging.getLogger("peewee")
peewee_logger.setLevel(logging.INFO)
database = SqliteDatabase(
    helper.db_path
    # This is commented out after presenting issues when
    # moving from SQLiteDatabase to SqliteQueueDatabase
    # //TODO Enable tuning
    # pragmas={"journal_mode": "wal", "cache_size": -1024 * 10}
)


class db_builder:
    @staticmethod
    def default_settings():
        logger.info("Fresh Install Detected - Creating Default Settings")
        console.info("Fresh Install Detected - Creating Default Settings")
        default_data = helper.find_default_password()

        username = default_data.get("username", "admin")
        password = default_data.get("password", "crafty")

        users_helper.add_user(
            username=username,
            password=password,
            email="default@example.com",
            superuser=True,
        )

    @staticmethod
    def is_fresh_install():
        try:
            user = users_helper.get_by_id(1)
            if user:
                return False
        except:
            return True


class db_shortcuts:

    # **********************************************************************************
    #                                  Generic Databse Methods
    # **********************************************************************************
    @staticmethod
    def return_rows(query):
        rows = []

        try:
            if query.count() > 0:
                for s in query:
                    rows.append(model_to_dict(s))
        except Exception as e:
            logger.warning(f"Database Error: {e}")

        return rows

    @staticmethod
    def return_db_rows(model):
        data = [model_to_dict(row) for row in model]
        return data


# **********************************************************************************
#                                  Static Accessors
# **********************************************************************************
installer = db_builder()
db_helper = db_shortcuts()
