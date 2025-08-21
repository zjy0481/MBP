# mbp_project/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('terminal_management.urls')), 
]

# --- 新增配置：仅在开发模式下生效 ---
if settings.DEBUG:
    # 这个辅助函数会自动添加所有已发现的静态文件路由，
    # 包括我们自己的 /static/ 目录和 django.contrib.admin 等应用自带的静态文件。
    urlpatterns += staticfiles_urlpatterns()
    