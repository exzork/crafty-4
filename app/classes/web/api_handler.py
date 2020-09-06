import os
import secrets
import threading
import tornado.web
import tornado.escape 
import logging

from app.classes.shared.models import Users

log = logging.getLogger(__name__)


class BaseHandler(tornado.web.RequestHandler):
    
    def return_response(self, data: dict):
        # Define a standardized response 
        self.write(data)
    
    def access_denied(self, user):
        log.info("User %s was denied access to API route", user)
        self.set_status(403)
        self.finish(self.return_response(403, {'error':'ACCESS_DENIED', 'info':'You were denied access to the requested resource'}))
    
    def authenticate_user(self, token):
        try:
            log.debug("Searching for specified token")
            user_data = Users.get(api_token=token)
            log.debug("Checking results")
            if user_data:
                # Login successful! Return the username
                log.info("User {} has authenticated to API".format(user_data.username))
                return user_data.username
            else:
                logging.debug("Auth unsuccessful")
                return None
        except:
            log.warning("Traceback occurred when authenticating user to API. Most likely wrong token")
            return None
            pass

