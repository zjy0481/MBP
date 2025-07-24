# terminal_management/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # 将根路径的websocket连接路由到MainConsumer
    re_path(r'ws/main/$', consumers.MainConsumer.as_asgi()),
]