import sys
import json
import logging
import tornado.web
import tornado.escape
import requests

from app.classes.shared.helpers import helper
from app.classes.web.base_handler import BaseHandler
from app.classes.shared.console import console
from app.classes.shared.main_models import Users, fn

logger = logging.getLogger(__name__)

try:
    import bleach

except ModuleNotFoundError as e:
    logger.critical("Import Error: Unable to load {} module".format(e.name), exc_info=True)
    console.critical("Import Error: Unable to load {} module".format(e.name))
    sys.exit(1)


class HTTPHandlerPage(BaseHandler):
    def get(self, page):
        url = self.request.full_url
        port = 443
        if url[len(url)-1] == '/':
            url = url.strip(url[len(url)-1])
        url_list = url.split('/')
        if url_list[0] != "":
            primary_url = url_list[0] + ":"+str(port)+"/"
            backup_url = url_list[0] + ":" +str(helper.get_setting["https_port"]) +"/"
            for i in range(len(url_list)-1):
                primary_url += url_list[i+1]
                backup_url += url_list[i+1]
        else:
            primary_url = url + str(port)
            backup_url = url + str(helper.get_setting['https_port'])
        
        try:
            resp = requests.get(primary_url)
            resp.raise_for_status()
            url = primary_url
        except Exception as err:
            url = backup_url
        self.redirect('https://'+url+':'+ str(port))