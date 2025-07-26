# mbp_project/asgi.py
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mbp_project.settings')
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack # 用于访问session和user
import terminal_management.routing

application = ProtocolTypeRouter({
    # 处理普通的HTTP请求
    "http": django_asgi_app,

    # 处理WebSocket请求
    "websocket": AuthMiddlewareStack(
        URLRouter(
            terminal_management.routing.websocket_urlpatterns
        )
    ),
})