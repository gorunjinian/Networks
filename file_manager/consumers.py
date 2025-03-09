import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from django.conf import settings
import hmac
import hashlib


class ProgressConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.progress_group_name = None
        self.user_id = None

    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.progress_group_name = f'progress_{self.user_id}'
        
        # Add user authentication validation
        try:
            # Get user from database to validate the user_id
            user = await self.get_user(self.user_id)
            
            if not user:
                # Reject the connection if user doesn't exist
                await self.close(code=4003)
                return
                
            # Store user in the instance for later reference
            self.user = user
            
            # Join progress group
            await self.channel_layer.group_add(
                self.progress_group_name,
                self.channel_name
            )

            await self.accept()
            
            # Send a connection established message
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'WebSocket connection established for progress updates'
            }))
            
        except Exception as e:
            logging.error(f"WebSocket connection error: {str(e)}")
            # Close the connection with an error code
            await self.close(code=4000)

    async def disconnect(self, close_code):
        # Leave progress group
        try:
            await self.channel_layer.group_discard(
                self.progress_group_name,
                self.channel_name
            )
        except Exception as e:
            logging.error(f"Error during WebSocket disconnect: {str(e)}")

    # Receive message from WebSocket
    async def receive(self, text_data):
        try:
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
            elif message_type == 'ping':
                # Handle ping-pong for connection health check
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': text_data_json.get('timestamp')
                }))
        except json.JSONDecodeError:
            logging.error("Invalid JSON received in WebSocket")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            logging.error(f"Error processing WebSocket message: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Server error processing message'
            }))

    # Receive progress update from progress group
    async def progress_update(self, event):
        try:
            # Send progress update to WebSocket
            await self.send(text_data=json.dumps({
                'type': 'progress_update',
                'filename': event.get('filename'),
                'progress': event.get('progress'),
                'speed': event.get('speed'),
                'action': event.get('action')
            }))
        except Exception as e:
            logging.error(f"Error sending progress update: {str(e)}")
    
    @sync_to_async
    def get_user(self, user_id):
        """Retrieve a user by ID"""
        try:
            return User.objects.filter(id=user_id).first()
        except Exception:
            return None

    def verify_token(self, user_id, token):
        """Verify the authenticity of the WebSocket connection token"""
        if not token:
            return False

        # Create expected token using HMAC with server secret
        expected_token = hmac.new(
            settings.SECRET_KEY.encode(),
            f"ws_auth_{user_id}".encode(),
            hashlib.sha256
        ).hexdigest()

        # Constant time comparison to prevent timing attacks
        return hmac.compare_digest(expected_token, token)
