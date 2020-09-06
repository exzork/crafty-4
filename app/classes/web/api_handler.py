import os
import secrets
import threading
import tornado.web
import tornado.escape 
import logging

from app.classes.shared.models import Users
from app.classes.minecraft.stats import stats

log = logging.getLogger(__name__)


class BaseHandler(tornado.web.RequestHandler):
    
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


class ServersStats(BaseHandler):
    def get(self):
        """Get details about all servers"""
        self.authenticate_user()
        # Get server stats
        self.finish(self.write({"servers": stats.get_servers_stats()}))


class NodeStats(BaseHandler):
    def get(self):
        """Get stats for particular node"""
        self.authenticate_user()
        # Get node stats
        node_stats = stats.get_node_stats()
        node_stats.pop("servers")
        self.finish(self.write(node_stats))
