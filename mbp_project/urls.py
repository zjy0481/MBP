# mbp_project/urls.py

from django.contrib import admin
from django.urls import path, include
# --- 新增导入 ---
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # 将所有根路径的请求都交给 terminal_management.urls 文件处理
    path('', include('terminal_management.urls')), 
]

# --- 新增配置：仅在开发模式下生效 ---
if settings.DEBUG:
    # 将 STATIC_URL (即 '/static/') 的请求路由到 STATICFILES_DIRS 指定的文件夹
    # 注意：STATICFILES_DIRS 是一个列表，我们取第一个元素
    # 这使得 Daphne 在开发时也能像 runserver 一样正确地提供静态文件服务
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])