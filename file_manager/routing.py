from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/progress/(?P<user_id>\w+)/$', consumers.ProgressConsumer.as_asgi()),
]
