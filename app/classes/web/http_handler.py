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
        url = str(self.request.full_url())
        port = 443
        db_port = helper.get_setting('https_port')
        if url[len(url)-1] == '/':
            url = url.strip(url[len(url)-1])

        url_list = url.split('/')
        new_url_list = url_list[2].split(':')

        if new_url_list[0] != "":
            url = 'https://' + new_url_list[0]
        else:
            url = 'https://' + url_list[2]

        if url_list[0] != "":
            primary_url = url + ":"+str(port)+"/"
            backup_url = url + ":" +str(db_port) +"/"
        else:
            primary_url = url +":" +str(port)
            backup_url = url + ":"+str(db_port)
        
        try:
            resp = requests.get(primary_url)
            resp.raise_for_status()
            url = primary_url
        except Exception as err:
            url = backup_url
        self.redirect(url)


class HTTPHandlerPage(BaseHandler):
    def get(self, page):
        url = str(self.request.full_url())
        port = 443
        db_port = helper.get_setting('https_port')
        if url[len(url)-1] == '/':
            url = url.strip(url[len(url)-1])

        url_list = url.split('/')
        new_url_list = url_list[2].split(':')

        if new_url_list[0] != "":
            url = 'https://' + new_url_list[0]
        else:
            url = 'https://' + url_list[2]

        if url_list[0] != "":
            primary_url = url + ":"+str(port)+"/"
            backup_url = url + ":" +str(db_port) +"/"
        else:
            primary_url = url +":" +str(port)
            backup_url = url + ":"+str(db_port)
        
        try:
            resp = requests.get(primary_url)
            resp.raise_for_status()
            url = primary_url
        except Exception as err:
            url = backup_url
        self.redirect(url)