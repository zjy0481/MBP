# mbp_project/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack # 用于访问session和user
import terminal_management.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MBP.settings')

application = ProtocolTypeRouter({
    # 处理普通的HTTP请求
    "http": get_asgi_application(),

    # 处理WebSocket请求
    "websocket": AuthMiddlewareStack(
        URLRouter(
            terminal_management.routing.websocket_urlpatterns
        )
    ),
})