import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Profile, Scenario, DirectMessage, ChatRoom, ChatMessage
from datetime import datetime

class DirectMessageConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.other_user_id = self.scope['url_route']['kwargs']['user_id']
        
        # Check if user is authenticated
        if self.user.is_anonymous:
            await self.close()
            return
            
        # Get the other user
        self.other_user = await self.get_user(self.other_user_id)
        if not self.other_user:
            await self.close()
            return
        
        # Create a unique channel group name for these two users
        user_ids = sorted([str(self.user.id), self.other_user_id])
        self.room_group_name = f'chat_{user_ids[0]}_{user_ids[1]}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type', 'message')
        message = text_data_json['message']
        recipient_id = int(self.other_user_id)
        
        # Save message to database
        if message_type == 'share_scenario':
            scenario_id = text_data_json.get('scenario_id')
            scenario_data = await self.get_scenario_data(scenario_id)
            
            # Save message with scenario
            await self.save_direct_message(self.user.id, recipient_id, message, scenario_id)
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'direct_message',
                    'message': message,
                    'username': self.user.username,
                    'user_id': self.user.id,
                    'message_type': 'scenario',
                    'scenario': scenario_data,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            )
        else:
            # Save regular message
            await self.save_direct_message(self.user.id, recipient_id, message)
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'direct_message',
                    'message': message,
                    'username': self.user.username,
                    'user_id': self.user.id,
                    'message_type': 'text',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            )

    # Receive message from room group
    async def direct_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': event['message_type'],
            'message': event['message'],
            'username': event['username'],
            'user_id': event['user_id'],
            'scenario': event.get('scenario'),
            'timestamp': event['timestamp']
        }))
    
    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_scenario_data(self, scenario_id):
        try:
            scenario = Scenario.objects.get(id=scenario_id)
            return {
                'id': scenario.id,
                'title': scenario.title,
                'description': scenario.description,
                'category': scenario.category,
                'difficulty': scenario.difficulty
            }
        except Scenario.DoesNotExist:
            return None
    
    @database_sync_to_async
    def save_direct_message(self, sender_id, recipient_id, content, scenario_id=None):
        sender = User.objects.get(id=sender_id)
        recipient = User.objects.get(id=recipient_id)
        
        message = DirectMessage(
            sender=sender,
            recipient=recipient,
            content=content
        )
        
        if scenario_id:
            try:
                scenario = Scenario.objects.get(id=scenario_id)
                message.shared_scenario = scenario
            except Scenario.DoesNotExist:
                pass
                
        message.save()
        return message

class CommunityConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.room_group_name = 'community_chat'
        
        # Check if user is authenticated
        if self.user.is_anonymous:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        
        # Save message to database
        await self.save_community_message(self.user.id, message)
        
        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'community_message',
                'message': message,
                'username': self.user.username,
                'user_id': self.user.id,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        )

    # Receive message from room group
    async def community_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'username': event['username'],
            'user_id': event['user_id'],
            'timestamp': event['timestamp']
        }))
    
    @database_sync_to_async
    def save_community_message(self, sender_id, content):
        sender = User.objects.get(id=sender_id)
        
        # Get or create a community chat room
        room, created = ChatRoom.objects.get_or_create(
            name="Community Chat",
            room_type="public",
            defaults={
                "created_by": sender,
                "description": "Public community chat room"
            }
        )
        
        # Add user to participants if not already there
        if not room.participants.filter(id=sender_id).exists():
            room.participants.add(sender)
            
        # Save the message
        message = ChatMessage(
            room=room,
            sender=sender,
            content=content
        )
        message.save()
        
        return message 

class ChatRoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_room_{self.room_id}'
        
        # Check if user is authenticated
        if self.user.is_anonymous:
            await self.close()
            return
        
        # Verify the user is a participant in this chat room
        is_participant = await self.is_room_participant()
        if not is_participant:
            await self.close()
            return
            
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        
        # Broadcast user online status
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'user_id': self.user.id,
                'username': self.user.username,
                'status': 'online',
            }
        )

    async def disconnect(self, close_code):
        # Broadcast user offline status before leaving
        if hasattr(self, 'room_group_name') and hasattr(self, 'user') and not self.user.is_anonymous:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'status': 'offline',
                }
            )
            
        # Leave room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    # Receive message from WebSocket
    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type', 'message')
            
            if message_type == 'typing':
                # Handle typing indicator
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'typing_status',
                        'user_id': self.user.id,
                        'username': self.user.username,
                        'is_typing': text_data_json.get('is_typing', False),
                    }
                )
            elif message_type == 'message':
                # Handle regular message
                message = text_data_json.get('message', '').strip()
                if message:
                    # Save message to database
                    message_obj = await self.save_room_message(self.user.id, message)
                    
                    # Send message to room group
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'chat_message',
                            'message': message,
                            'message_id': message_obj.id,
                            'username': self.user.username,
                            'user_id': self.user.id,
                            'timestamp': message_obj.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                        }
                    )
        except json.JSONDecodeError:
            print("Invalid JSON received")
        except Exception as e:
            print(f"Error in receive: {str(e)}")

    # Receive message from room group
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message_id': event['message_id'],
            'message': event['message'],
            'username': event['username'],
            'user_id': int(event['user_id']),
            'timestamp': event['timestamp'],
            'is_own': int(event['user_id']) == self.user.id
        }))
    
    # Handle typing status updates
    async def typing_status(self, event):
        # Send typing status to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_typing': event['is_typing']
        }))
    
    # Handle user status updates
    async def user_status(self, event):
        # Send user status to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'status',
            'user_id': event['user_id'],
            'username': event['username'],
            'status': event['status']
        }))
    
    @database_sync_to_async
    def is_room_participant(self):
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            return room.participants.filter(id=self.user.id).exists()
        except ChatRoom.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_room_message(self, sender_id, content):
        sender = User.objects.get(id=sender_id)
        room = ChatRoom.objects.get(id=self.room_id)
        
        # Update the room's updated_at timestamp
        room.updated_at = datetime.now()
        room.save(update_fields=['updated_at'])
        
        # Save the message
        message = ChatMessage(
            room=room,
            sender=sender,
            content=content
        )
        message.save()
        
        return message 