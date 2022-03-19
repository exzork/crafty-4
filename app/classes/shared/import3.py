import json
import os
import console
import logging
logger = logging.getLogger(__name__)

from app.classes.controllers.users_controller import users_helper
from app.classes.shared.main_controller import Controller

class import3:
    def start_import(self):
        folder = os.path.normpath(input("Please input the path to the migrations folder in your installation of Crafty 3: "))
        if not os.path.exists(folder):
            console.log("Crafty cannot find the path you entered. Does Crafty's user have permission to access it?")
            console.log("Please run the import3 command again and enter a valid path.")
        else:
            with open (os.path.join(folder, "users.json")) as f:
                user_json = json.load(f.read())
            with open (os.path.join(folder, "mc_settings.json")) as f:
                servers_json = json.load(f.read())
            self.import_users(user_json)
            self.import_servers(servers_json)

    @staticmethod
    def import_users(json_data):
        for user in json_data:
            users_helper.add_rawpass_user(user.username, user.password)
            console.log(f"Imported user {user.username} from Crafty 3")
            logger.info(f"Imported user {user.username} from Crafty 3")

    @staticmethod
    def import_servers(json_data):
        return