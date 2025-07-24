# mbp_project/urls.py
from django.contrib import admin
# 引入 include 函数
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # 将所有根路径的请求都交给 terminal_management.urls 文件处理
    path('', include('terminal_management.urls')), 
]