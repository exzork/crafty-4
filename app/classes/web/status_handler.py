import logging

from app.classes.shared.helpers import helper
from app.classes.web.base_handler import BaseHandler

from app.classes.shared.server import Server

logger = logging.getLogger(__name__)

class StatusHandler(BaseHandler):
    def get(self):
        page_data = {}
        page_data['lang'] = helper.get_setting('language')
        page_data['servers'] = self.controller.servers.get_all_servers_stats()
        for srv in page_data['servers']:
            server_data = srv.get('server_data', False)
            server_id = server_data.get('server_id', False)
            srv['raw_ping_result'] = self.controller.servers.get_server_stats_by_id(server_id)
            srv['raw_ping_result']
            {
                'icon': False,
            }

        template = 'public/status.html'

        self.render(
        template,
        data=page_data,
        translate=self.translator.translate,
    )
    def post(self):
        page_data = {}
        page_data['servers'] = self.controller.servers.get_all_servers_stats()
        for srv in page_data['servers']:
            server_data = srv.get('server_data', False)
            server_id = server_data.get('server_id', False)
            srv['raw_ping_result'] = self.controller.servers.get_server_stats_by_id(server_id)
            {
                'icon': False,
            }

        template = 'public/status.html'

        self.render(
        template,
        data=page_data,
        translate=self.translator.translate,
    )
