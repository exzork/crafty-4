import logging
import requests

from app.classes.web.base_handler import BaseHandler

logger = logging.getLogger(__name__)


class HTTPHandler(BaseHandler):
    def get(self):
        url = str(self.request.host)
        port = 443
        url_list = url.split(":")
        if url_list[0] != "":
            url = "https://" + url_list[0]
        else:
            url = "https://" + url
        db_port = self.helper.get_setting("https_port")
        try:
            resp = requests.get(url + ":" + str(port))
            resp.raise_for_status()
        except Exception:
            port = db_port
        self.redirect(url + ":" + str(port))


class HTTPHandlerPage(BaseHandler):
    def get(self):
        url = str(self.request.host)
        port = 443
        url_list = url.split(":")
        if url_list[0] != "":
            url = "https://" + url_list[0]
        else:
            url = "https://" + url
        db_port = self.helper.get_setting("https_port")
        try:
            resp = requests.get(url + ":" + str(port))
            resp.raise_for_status()
        except Exception:
            port = db_port
        self.redirect(url + ":" + str(port))
