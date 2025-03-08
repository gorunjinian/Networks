import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User


class ProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.progress_group_name = f'progress_{self.user_id}'

        # Join progress group
        await self.channel_layer.group_add(
            self.progress_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave progress group
        await self.channel_layer.group_discard(
            self.progress_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type')
        
        if message_type == 'progress_update':
            # Send progress update to progress group
            await self.channel_layer.group_send(
                self.progress_group_name,
                {
                    'type': 'progress_update',
                    'filename': text_data_json.get('filename'),
                    'progress': text_data_json.get('progress'),
                    'speed': text_data_json.get('speed'),
                    'action': text_data_json.get('action')
                }
            )

    # Receive progress update from progress group
    async def progress_update(self, event):
        # Send progress update to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'progress_update',
            'filename': event.get('filename'),
            'progress': event.get('progress'),
            'speed': event.get('speed'),
            'action': event.get('action')
        }))
