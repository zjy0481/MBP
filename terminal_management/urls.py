# terminal_management/urls.py

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # --- 首页 ---
    path('', views.home, name='home'),

    # --- 认证功能 ---
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),

    # --- 船舶管理功能 ---
    path('ships/', views.ship_list, name='ship_list'),
    path('ships/add/', views.ship_create, name='ship_create'),
    # <str:mmsi> 会捕获URL中的字符串，并作为参数传递给视图函数
    path('ships/<str:mmsi>/edit/', views.ship_update, name='ship_update'),
    path('ships/<str:mmsi>/delete/', views.ship_delete, name='ship_delete'),

    # --- 端站管理功能 ---
    path('terminals/', views.terminal_list, name='terminal_list'),
    path('terminals/add/', views.terminal_create, name='terminal_create'),
    path('terminals/<str:sn>/edit/', views.terminal_update, name='terminal_update'),
    path('terminals/<str:sn>/delete/', views.terminal_delete, name='terminal_delete'),

    # --- 基站管理功能 ---
    path('base-stations/', views.base_station_list, name='base_station_list'),
    path('base-stations/add/', views.base_station_create, name='base_station_create'),
    path('base-stations/<str:bts_id>/edit/', views.base_station_update, name='base_station_update'),
    path('base-stations/<str:bts_id>/delete/', views.base_station_delete, name='base_station_delete'),

    # --- 端站数据与控制 ---
    path('antenna/', views.antenna, name='antenna'),

    # --- 端站系统管理 ---
    path('systemmanage/', views.systemmanage, name='systemmanage'),

    # --- GIS ---
    path('gis/', views.gis_page, name='gis_page'),
    path('api/get_track/', views.get_ship_track, name='get_ship_track'),
]