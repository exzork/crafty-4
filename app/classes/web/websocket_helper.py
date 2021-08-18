import json
import logging
import sys, threading, asyncio

from app.classes.shared.console import console

logger = logging.getLogger(__name__)


try:
    import tornado.ioloop

except ModuleNotFoundError as e:
    logger.critical("Import Error: Unable to load {} module".format(e, e.name))
    console.critical("Import Error: Unable to load {} module".format(e, e.name))
    sys.exit(1)

class WebSocketHelper:
    def __init__(self):
        self.clients = set()

    def add_client(self, client):
        self.clients.add(client)
    
    def remove_client(self, client):
        self.clients.remove(client)

    def send_message(self, client, event_type: str, data):
        if client.check_auth():
            message = str(json.dumps({'event': event_type, 'data': data}))
            client.write_message_helper(message)

    def broadcast(self, event_type: str, data):
        logger.debug('Sending to {} clients: {}'.format(len(self.clients), json.dumps({'event': event_type, 'data': data})))
        for client in self.clients:
            try:
                self.send_message(client, event_type, data)
            except Exception as e:
                logger.exception('Error catched while sending WebSocket message to {}'.format(client.get_remote_ip()))

    def broadcast_page(self, page: str, event_type: str, data):
        def filter_fn(client):
            return client.page == page

        clients = list(filter(filter_fn, self.clients))

        logger.debug('Sending to {} out of {} clients: {}'.format(len(clients), len(self.clients), json.dumps({'event': event_type, 'data': data})))

        for client in clients:
            try:
                self.send_message(client, event_type, data)
            except Exception as e:
                logger.exception('Error catched while sending WebSocket message to {}'.format(client.get_remote_ip()))
    
    def broadcast_page_params(self, page: str, params: dict, event_type: str, data):
        def filter_fn(client):
            if client.page != page:
                return False
            for key, param in params.items():
                if param != client.page_query_params.get(key, None):
                    return False
            return True

        clients = list(filter(filter_fn, self.clients))

        logger.debug('Sending to {} out of {} clients: {}'.format(len(clients), len(self.clients), json.dumps({'event': event_type, 'data': data})))

        for client in clients:
            try:
                self.send_message(client, event_type, data)
            except Exception as e:
                logger.exception('Error catched while sending WebSocket message to {}'.format(client.get_remote_ip()))
    
    def disconnect_all(self):
        console.info('Disconnecting WebSocket clients')
        for client in self.clients:
            client.close()
        console.info('Disconnected WebSocket clients')

websocket_helper = WebSocketHelper()