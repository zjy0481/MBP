# terminal_management/routing.py

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # 匹配 ws://yourdomain/ws/data/ 这样的 URL
    re_path(r'ws/data/$', consumers.DataConsumer.as_asgi()),
]