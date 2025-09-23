# terminal_management/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from . import services
from .forms import ShipInfoForm
from .forms import TerminalInfoForm
from .forms import BaseStationInfoForm
from django.http import JsonResponse
from datetime import datetime

def home(request):
    """
    首页的视图函数。
    它只是简单地渲染一个静态的 home.html 页面。
    """
    return render(request, 'home.html')

def logout_view(request):
    """
    处理用户登出并显示自定义的登出成功页面。
    """
    logout(request)
    return render(request, 'logout.html')

def register(request):
    """
    用户注册的视图函数。
    """
    if request.method == 'POST':
        # 如果是POST请求，说明用户提交了注册表单
        form = UserCreationForm(request.POST)
        if form.is_valid():
            # 表单验证通过，创建新用户
            user = form.save()
            # 注册后自动登录
            login(request, user)
            # 跳转到首页
            return redirect('home')
    else:
        # 如果是GET请求，显示一个空的注册表单
        form = UserCreationForm()
    
    return render(request, 'register.html', {'form': form})

# --- 船舶管理视图 ---

@login_required # 这个装饰器确保只有登录用户才能访问此视图
def ship_list(request):
    """显示所有船舶的列表"""
    success, ships_or_error = services.get_all_ships()
    context = {
        'ships': ships_or_error if success else [],
        'error': None if success else ships_or_error
    }
    return render(request, 'ship_list.html', context)

@login_required
def ship_create(request):
    """创建新船舶"""
    if request.method == 'POST':
        form = ShipInfoForm(request.POST)
        if form.is_valid():
            # 表单数据有效，调用服务层函数创建船舶
            data = form.cleaned_data
            success, result_or_error = services.create_ship(**data)
            if success:
                # 创建成功，重定向到船舶列表页面
                return redirect('ship_list')
            else:
                # 创建失败，将错误信息添加到表单中以便在页面上显示
                form.add_error(None, result_or_error)
    else:
        form = ShipInfoForm()
    
    return render(request, 'ship_form.html', {'form': form, 'form_title': '添加新船舶'})

@login_required
def ship_update(request, mmsi):
    """编辑船舶信息"""
    success, ship_or_error = services.get_ship_by_mmsi(mmsi)
    if not success:
        return redirect('ship_list')

    ship = ship_or_error

    if request.method == 'POST':
        form = ShipInfoForm(request.POST, instance=ship)
        if form.is_valid():
            # 手动构建参数，避免冲突和名称不匹配
            data = form.cleaned_data
            success, result_or_error = services.update_ship(
                mmsi=mmsi,  # mmsi 来自 URL，作为定位符
                new_ship_name=data['ship_name'],
                new_call_sign=data['call_sign'],
                new_ship_owner=data['ship_owner']
            )

            if success:
                return redirect('ship_list')
            else:
                form.add_error(None, result_or_error)
    else:
        form = ShipInfoForm(instance=ship)

    return render(request, 'ship_form.html', {'form': form, 'form_title': f'编辑船舶: {ship.ship_name}'})

@login_required
def ship_delete(request, mmsi):
    """删除船舶"""
    success, ship_or_error = services.get_ship_by_mmsi(mmsi)
    if not success:
        return redirect('ship_list')
    
    ship = ship_or_error

    if request.method == 'POST':
        # 确认删除
        services.delete_ship(mmsi)
        return redirect('ship_list')

    # 复用 data_confirm_delete.html 模板
    return render(request, 'data_confirm_delete.html', {'item': ship})


# --- 端站管理视图 ---

@login_required
def terminal_list(request):
    """显示所有端站的列表"""
    success, terminals_or_error = services.get_all_terminals()
    context = {
        'terminals': terminals_or_error if success else [],
        'error': None if success else terminals_or_error
    }
    return render(request, 'terminal_list.html', context)

@login_required
def terminal_create(request):
    """创建新端站"""
    if request.method == 'POST':
        form = TerminalInfoForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            ship_mmsi = data['ship'].mmsi

            # 调用 services.create_terminal
            success, result_or_error = services.create_terminal(
                sn=data['sn'],
                ship_mmsi=ship_mmsi,
                # 使用 .get() 来安全地获取可选字段
                ip_address=data.get('ip_address'),
                port_number=data.get('port_number')
            )
            if success:
                #messages.success(request, f"端站 {result_or_error.sn} 创建成功！")
                return redirect('terminal_list')
                
            else:
                form.add_error(None, result_or_error)
    else:
        form = TerminalInfoForm()
    
    return render(request, 'terminal_form.html', {'form': form, 'form_title': '添加新端站'})

@login_required
def terminal_update(request, sn):
    """编辑端站信息"""
    success, terminal_or_error = services.get_terminal_by_sn(sn)
    if not success:
        messages.error(request, terminal_or_error)
        return redirect('terminal_list')
    
    terminal = terminal_or_error

    if request.method == 'POST':
        form = TerminalInfoForm(request.POST, instance=terminal)
        if form.is_valid():
            data = form.cleaned_data
            # 从表单数据中获取新选择的船舶的 mmsi
            new_ship_mmsi = data['ship'].mmsi
            
            success, result_or_error = services.update_terminal(
                sn=sn,
                new_ship_mmsi=new_ship_mmsi,
                new_ip_address=data.get('ip_address'),
                new_port_number=data.get('port_number')
            )
            if success:
                messages.success(request, f"端站 {result_or_error.sn} 更新成功！")
                return redirect('terminal_list')
            else:
                form.add_error(None, result_or_error)
    else:
        form = TerminalInfoForm(instance=terminal)

    return render(request, 'terminal_form.html', {'form': form, 'form_title': f'编辑端站: {terminal.sn}'})

@login_required
def terminal_delete(request, sn):
    """删除端站"""
    success, terminal_or_error = services.get_terminal_by_sn(sn)
    if not success:
        return redirect('terminal_list')
    
    terminal = terminal_or_error

    if request.method == 'POST':
        services.delete_terminal(sn)
        return redirect('terminal_list')

    # 复用 data_confirm_delete.html 模板
    return render(request, 'data_confirm_delete.html', {'item': terminal})


# --- 基站管理视图 ---

@login_required
def base_station_list(request):
    """显示所有基站的列表"""
    success, stations_or_error = services.get_all_base_stations()
    context = {
        'stations': stations_or_error if success else [],
        'error': None if success else stations_or_error
    }
    return render(request, 'base_station_list.html', context)

@login_required
def base_station_create(request):
    """创建新基站"""
    if request.method == 'POST':
        form = BaseStationInfoForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            success, result_or_error = services.create_base_station(**data)
            if success:
                return redirect('base_station_list')
            else:
                form.add_error(None, result_or_error)
    else:
        form = BaseStationInfoForm()
    
    return render(request, 'base_station_form.html', {'form': form, 'form_title': '添加新基站'})

@login_required
def base_station_update(request, bts_id):
    """编辑基站信息"""
    success, station_or_error = services.get_base_station_by_id(bts_id)
    if not success:
        return redirect('base_station_list')
    
    station = station_or_error

    if request.method == 'POST':
        form = BaseStationInfoForm(request.POST, instance=station)
        if form.is_valid():
            data = form.cleaned_data
            data.pop('bts_id', None)
            success, result_or_error = services.update_base_station(bts_id=bts_id, **data)
            if success:
                return redirect('base_station_list')
            else:
                form.add_error(None, result_or_error)
    else:
        form = BaseStationInfoForm(instance=station)
        # 基站ID(主键)在编辑时不应被修改，所以我们禁用该输入框
        form.fields['bts_id'].widget.attrs['readonly'] = True

    return render(request, 'base_station_form.html', {'form': form, 'form_title': f'编辑基站: {station.bts_name}'})

@login_required
def base_station_delete(request, bts_id):
    """删除基站"""
    success, station_or_error = services.get_base_station_by_id(bts_id)
    if not success:
        return redirect('base_station_list')
    
    station = station_or_error

    if request.method == 'POST':
        services.delete_base_station(bts_id)
        return redirect('base_station_list')

    # 复用 data_confirm_delete.html 模板
    return render(request, 'data_confirm_delete.html', {'item': station})

# --- 端站数据与控制视图 ---

@login_required
def antenna(request):
    """渲染端站数据与控制页面"""
    success, terminals_or_error = services.get_all_terminals()
    context = {
        'terminals': terminals_or_error if success else [],
        'error': None if success else terminals_or_error
    }
    return render(request, 'antenna.html', context)

# --- 端站系统管理视图 ---

@login_required
def systemmanage(request):
    """渲染端站系统管理页面"""
    success, terminals_or_error = services.get_all_terminals()
    context = {
        'terminals': terminals_or_error if success else [],
        'error': None if success else terminals_or_error
    }
    return render(request, 'systemmanage.html', context)

# --- GIS 视图 ---
@login_required
def gis_page(request):
    """渲染 GIS 地图页面"""
    success, ships_or_error = services.get_all_ships()
    context = {
        'ships': ships_or_error if success else [],
        'error': None if success else ships_or_error
    }
    return render(request, 'gis.html', context)

@login_required
def get_ship_track(request):
    """获取指定船舶在特定时间范围内的轨迹点数据API"""
    mmsi = request.GET.get('mmsi')
    start_time_str = request.GET.get('start_time')
    end_time_str = request.GET.get('end_time')

    if not all([mmsi, start_time_str, end_time_str]):
        return JsonResponse({'error': '缺少必要的参数(mmsi, start_time, end_time)'}, status=400)

    try:
        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.fromisoformat(end_time_str)
    except ValueError:
        return JsonResponse({'error': '时间格式无效，请使用ISO 8601格式'}, status=400)

    # 步骤 1: 首先获取船舶信息
    ship_success, ship_or_error = services.get_ship_by_mmsi(mmsi)
    if not ship_success:
        return JsonResponse({'error': ship_or_error}, status=404)
    ship = ship_or_error

    # 步骤 2: 获取该船的轨迹报告
    success, reports_or_error = services.get_reports_by_mmsi_and_time(mmsi, start_time, end_time)
    if not success:
        return JsonResponse({'error': str(reports_or_error)}, status=500)

    # 步骤 3: 序列化数据，不再进行错误的跨表查询
    track_data = list(reports_or_error.values(
        'sn', 'report_date', 'report_time', 'long', 'lat', 'yaw', 'bts_name', 'standard', 'pci', 'rsrp', 'sinr', 'rssi'
    ))

    # 步骤 4: 手动附加船舶信息并格式化时间
    for report in track_data:
        report['report_date'] = report['report_date'].isoformat()
        report['report_time'] = report['report_time'].isoformat()
        # 将从步骤1获取的船舶信息附加到每条记录中
        report['ship_name'] = ship.ship_name
        report['mmsi'] = ship.mmsi
        report['ship_owner'] = ship.ship_owner

    return JsonResponse(track_data, safe=False)