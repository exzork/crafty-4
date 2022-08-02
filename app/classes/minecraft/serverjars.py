import json
import threading
import time
import shutil
import logging
from datetime import datetime
import requests

from app.classes.controllers.servers_controller import ServersController
from app.classes.models.server_permissions import PermissionsServers

logger = logging.getLogger(__name__)


class ServerJars:
    def __init__(self, helper):
        self.helper = helper
        self.base_url = "https://serverjars.com"

    def _get_api_result(self, call_url: str):
        full_url = f"{self.base_url}{call_url}"

        try:
            response = requests.get(full_url, timeout=2)
            response.raise_for_status()
            api_data = json.loads(response.content)
        except Exception as e:
            logger.error(f"Unable to load {full_url} api due to error: {e}")
            return {}

        api_result = api_data.get("status")
        api_response = api_data.get("response", {})

        if api_result != "success":
            logger.error(f"Api returned a failed status: {api_result}")
            return {}

        return api_response

    def _read_cache(self):
        cache_file = self.helper.serverjar_cache
        cache = {}
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)

        except Exception as e:
            logger.error(f"Unable to read serverjars.com cache file: {e}")

        return cache

    def get_serverjar_data(self):
        data = self._read_cache()
        return data.get("servers")

    def _check_api_alive(self):
        logger.info("Checking serverjars.com API status")

        check_url = f"{self.base_url}/api/fetchTypes"
        try:
            response = requests.get(check_url, timeout=2)

            if response.status_code in [200, 201]:
                logger.info("Serverjars.com API is alive")
                return True
        except Exception as e:
            logger.error(f"Unable to connect to serverjar.com api due to error: {e}")
            return {}

        logger.error("unable to contact serverjars.com api")
        return False

    def refresh_cache(self):

        cache_file = self.helper.serverjar_cache
        cache_old = self.helper.is_file_older_than_x_days(cache_file)

        # debug override
        # cache_old = True

        # if the API is down... we bomb out
        if not self._check_api_alive():
            return False

        logger.info("Checking Cache file age")
        # if file is older than 1 day

        if cache_old:
            logger.info("Cache file is over 1 day old, refreshing")
            now = datetime.now()
            data = {"last_refreshed": now.strftime("%m/%d/%Y, %H:%M:%S"), "servers": {}}

            jar_types = self._get_server_type_list()

            # for each jar type
            for j in jar_types:

                # for each server
                for s in jar_types.get(j):
                    # jar versions for this server
                    versions = self._get_jar_details(s)

                    # add these versions (a list) to the dict with
                    # a key of the server type
                    data["servers"].update({s: versions})

            # save our cache
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    f.write(json.dumps(data, indent=4))
                    logger.info("Cache file refreshed")

            except Exception as e:
                logger.error(f"Unable to update serverjars.com cache file: {e}")

    def _get_jar_details(self, jar_type="servers"):
        url = f"/api/fetchAll/servers/{jar_type}"
        response = self._get_api_result(url)
        temp = []
        for v in response:
            temp.append(v.get("version"))
        time.sleep(0.5)
        return temp

    def _get_server_type_list(self):
        url = "/api/fetchTypes/"
        response = self._get_api_result(url)
        return response

    def download_jar(self, server, version, path, server_id):
        update_thread = threading.Thread(
            name=f"server_download-{server_id}-{server}-{version}",
            target=self.a_download_jar,
            daemon=True,
            args=(server, version, path, server_id),
        )
        update_thread.start()

    def a_download_jar(self, server, version, path, server_id):
        # delaying download for server register to finish
        time.sleep(3)
        fetch_url = f"{self.base_url}/api/fetchJar/servers/{server}/{version}"
        server_users = PermissionsServers.get_server_user_list(server_id)

        # We need to make sure the server is registered before
        # we submit a db update for it's stats.
        while True:
            try:
                ServersController.set_download(server_id)
                for user in server_users:
                    self.helper.websocket_helper.broadcast_user(
                        user, "send_start_reload", {}
                    )

                break
            except Exception as ex:
                logger.debug(f"server not registered yet. Delaying download - {ex}")

        # open a file stream
        with requests.get(fetch_url, timeout=2, stream=True) as r:
            try:
                with open(path, "wb") as output:
                    shutil.copyfileobj(r.raw, output)
                    ServersController.finish_download(server_id)

                    for user in server_users:
                        self.helper.websocket_helper.broadcast_user(
                            user, "notification", "Executable download finished"
                        )
                        time.sleep(3)
                        self.helper.websocket_helper.broadcast_user(
                            user, "send_start_reload", {}
                        )
                    return True
            except Exception as e:
                logger.error(f"Unable to save jar to {path} due to error:{e}")
                ServersController.finish_download(server_id)
                server_users = PermissionsServers.get_server_user_list(server_id)
                for user in server_users:
                    self.helper.websocket_helper.broadcast_user(
                        user, "notification", "Executable download finished"
                    )
                    time.sleep(3)
                    self.helper.websocket_helper.broadcast_user(
                        user, "send_start_reload", {}
                    )

                return False
