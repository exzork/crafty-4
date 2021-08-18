import os
import secrets
import threading
import tornado.web
import tornado.escape 
import logging

from app.classes.web.base_handler import BaseHandler
from app.classes.shared.models import db_shortcuts

log = logging.getLogger(__name__)


class ApiHandler(BaseHandler):
    
    def return_response(self, status: int, data: dict):
        # Define a standardized response 
        self.set_status(status)
        self.write(data)
    
    def access_denied(self, user, reason=''):
        if reason: reason = ' because ' + reason
        log.info("User %s from IP %s was denied access to the API route " + self.request.path + reason, user, self.get_remote_ip())
        self.finish(self.return_response(403, {
            'error':'ACCESS_DENIED',
            'info':'You were denied access to the requested resource'
        }))
    
    def authenticate_user(self) -> bool:
        try:
            log.debug("Searching for specified token")
            # TODO: YEET THIS
            user_data = db_shortcuts.get_user_by_api_token(self.get_argument('token'))
            log.debug("Checking results")
            if user_data:
                # Login successful! Check perms
                log.info("User {} has authenticated to API".format(user_data['username']))
                # TODO: Role check 

                return True # This is to set the "authenticated"
            else:
                logging.debug("Auth unsuccessful")
                self.access_denied("unknown", "the user provided an invalid token")
                return
        except Exception as e:
            log.warning("An error occured while authenticating an API user: %s", e)
            self.access_denied("unknown"), "an error occured while authenticating the user"
            return


class ServersStats(ApiHandler):
    def get(self):
        """Get details about all servers"""
        authenticated = self.authenticate_user()
        if not authenticated: return
        # Get server stats
        # TODO Check perms
        self.finish(self.write({"servers": self.controller.stats.get_servers_stats()}))


class NodeStats(ApiHandler):
    def get(self):
        """Get stats for particular node"""
        authenticated = self.authenticate_user()
        if not authenticated: return
        # Get node stats
        node_stats = self.controller.stats.get_node_stats()
        node_stats.pop("servers")
        self.finish(self.write(node_stats))
