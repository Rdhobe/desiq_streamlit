from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<user_id>\d+)/$', consumers.DirectMessageConsumer.as_asgi()),
    re_path(r'ws/community/$', consumers.CommunityConsumer.as_asgi()),
    re_path(r'ws/chat-room/(?P<room_id>\d+)/$', consumers.ChatRoomConsumer.as_asgi()),
] 