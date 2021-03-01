import json

from app.classes.shared.console import console

class WebSocketHelper:
    clients = set()

    def addClient(self, client):
        self.clients.add(client)
    
    def removeClient(self, client):
        self.clients.add(client)
    
    def send_message(self, client, event_type, data):
        if client.check_auth():
            message = str(json.dumps({'event': event_type, 'data': data}))
            client.write_message(message)

    def broadcast(self, event_type, data):
        console.debug('Sending: ' + str(json.dumps({'event': event_type, 'data': data})))
        for client in self.clients:
            try:
                self.send_message(client, event_type, data)
            except:
                pass
    
    def disconnect_all(self):
        console.info('Disconnecting WebSocket clients')
        for client in self.clients:
            client.close()
        console.info('Disconnected WebSocket clients')

websocket_helper = WebSocketHelper()