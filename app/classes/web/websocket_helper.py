import json

from app.classes.shared.console import console

class WebSocketHelper:
    clients = set()

    def addClient(self, client):
        self.clients.add(client)
    
    def removeClient(self, client):
        self.clients.add(client)

    def broadcast(self, message_type: str, data):
        console.debug('Sending: ' + str(json.dumps({'type': message_type, 'data': data})))
        message = str(json.dumps({'event': message_type, 'data': data}))
        for client in self.clients:
            try:
                client.write_message(message)
            except:
                pass
    
    def disconnect_all(self):
        console.info('Disconnecting WebSocket clients')
        for client in self.clients:
            client.close()
        console.info('Disconnected WebSocket clients')

websocket_helper = WebSocketHelper()