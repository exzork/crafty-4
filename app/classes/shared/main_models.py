import os
import sys
import logging
import datetime

from app.classes.shared.helpers import helper
from app.classes.shared.console import console
from app.classes.models.users import Users, users_helper
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
        user_id = users_helper.add_user(username, password=password, superuser=True)
        #users_helper.update_user(user_id, user_crafty_data={"permissions_mask":"111", "server_quantity":[-1,-1,-1]} )

        #console.info("API token is {}".format(api_token))

    @staticmethod
    def is_fresh_install():
        try:
            user = users_helper.get_by_id(1)
            return False
        except:
            return True
            pass

class db_shortcuts:

    #************************************************************************************************
    #                                  Generic Databse Methods
    #************************************************************************************************
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
    def return_db_rows(model):
        data = [model_to_dict(row) for row in model]
        return data
     

#************************************************************************************************
#                                  Static Accessors 
#************************************************************************************************
installer = db_builder()
db_helper = db_shortcuts()
