import sys
import json
import logging
import tornado.web
import tornado.escape
import requests

from app.classes.shared.helpers import helper
from app.classes.web.base_handler import BaseHandler
from app.classes.shared.console import console
from app.classes.shared.models import Users, fn, db_helper

logger = logging.getLogger(__name__)

try:
    import bleach

except ModuleNotFoundError as e:
    logger.critical("Import Error: Unable to load {} module".format(e.name), exc_info=True)
    console.critical("Import Error: Unable to load {} module".format(e.name))
    sys.exit(1)


class HTTPHandler(BaseHandler):
    def get(self):
        url = str(self.request.host)
        port = 443
        url_list = url.split(":")
        if url_list[0] != "":
            url = 'https://' + url_list[0]
        else:
            url = 'https://' + url
        db_port = helper.get_setting('https_port')
        try:
            resp = requests.get(url + ":" + str(port))
            resp.raise_for_status()
        except Exception as err:
            port = db_port
        self.redirect(url+":"+str(port))


class HTTPHandlerPage(BaseHandler):
    def get(self, page):
        url = str(self.request.host)
        port = 443
        url_list = url.split(":")
        if url_list[0] != "":
            url = 'https://' + url_list[0]
        else:
            url = 'https://' + url
        db_port = helper.get_setting('https_port')
        try:
            resp = requests.get(url + ":" + str(port))
            resp.raise_for_status()
        except Exception as err:
            port = db_port
        self.redirect(url+":"+str(port))