from re import template
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


class StatusHandler(BaseHandler):
    def get(self):
        page_data = {}
        page_data['servers'] = db_helper.get_all_servers_stats()

        template = 'public/status.html'

        self.render(
        template,
        data=page_data,
        translate=self.translator.translate,
    )
    def post(self):
        page_data = {}
        page_data['servers'] = db_helper.get_all_servers_stats()

        template = 'public/status.html'

        self.render(
        template,
        data=page_data,
        translate=self.translator.translate,
    )