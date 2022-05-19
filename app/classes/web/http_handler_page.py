import logging
import requests
from app.classes.web.base_handler import BaseHandler

logger = logging.getLogger(__name__)


class HTTPHandlerPage(BaseHandler):
    def get(self):
        url = self.request.full_url
        port = 443
        if url[len(url) - 1] == "/":
            url = url.strip(url[len(url) - 1])
        url_list = url.split("/")
        if url_list[0] != "":
            primary_url = url_list[0] + ":" + str(port) + "/"
            backup_url = (
                url_list[0] + ":" + str(self.helper.get_setting("https_port")) + "/"
            )
            for i in range(len(url_list) - 1):
                primary_url += url_list[i + 1]
                backup_url += url_list[i + 1]
        else:
            primary_url = url + str(port)
            backup_url = url + str(self.helper.get_setting("https_port"))

        try:
            resp = requests.get(primary_url)
            resp.raise_for_status()
            url = primary_url
        except Exception:
            url = backup_url
        self.redirect("https://" + url + ":" + str(port))
