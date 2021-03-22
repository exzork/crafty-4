import os
import secrets
import threading
import tornado.web
import tornado.escape 
import logging

from app.classes.web.base_handler import BaseHandler
from app.classes.shared.models import Users

log = logging.getLogger(__name__)


class ApiHandler(BaseHandler):
    
    def return_response(self, data: dict):
        # Define a standardized response 
        self.write(data)
    
    def access_denied(self, user):
        log.info("User %s was denied access to API route", user)
        self.set_status(403)
        self.finish(self.return_response(403, {'error':'ACCESS_DENIED', 'info':'You were denied access to the requested resource'}))
    
    def authenticate_user(self):
        try:
            log.debug("Searching for specified token")
            # TODO: YEET THIS
            user_data = Users.get(api_token=self.get_argument('token'))
            log.debug("Checking results")
            if user_data:
                # Login successful! Check perms
                log.info("User {} has authenticated to API".format(user_data.username))
                # TODO: Role check 
            else:
                logging.debug("Auth unsuccessful")
                return self.access_denied("unknown")
        except:
            log.warning("Traceback occurred when authenticating user to API. Most likely wrong token")
            return self.access_denied("unknown")
            pass


class ServersStats(ApiHandler):
    def get(self):
        """Get details about all servers"""
        self.authenticate_user()
        # Get server stats
        self.finish(self.write({"servers": self.controller.stats.get_servers_stats()}))


class NodeStats(ApiHandler):
    def get(self):
        """Get stats for particular node"""
        self.authenticate_user()
        # Get node stats
        node_stats = self.controller.stats.get_node_stats()
        node_stats.pop("servers")
        self.finish(self.write(node_stats))
