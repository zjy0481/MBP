# terminal_management/services.py

from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from .models import ShipInfo, TerminalInfo, BaseStationInfo, TerminalReport
from django.db.models import Q
from django.utils import timezone
from utils import gl_logger
from datetime import datetime

# -----------------------------------------------------------------------------
# 统一的返回格式说明
# -----------------------------------------------------------------------------
# 为了让调用方能清晰地知道操作是否成功，
# 我们约定所有函数都返回一个元组 (success, result_or_error_message)
# - success: 布尔值，True 表示操作成功，False 表示失败。
# - result_or_error_message: 成功时，返回查询到的对象或成功信息；失败时，返回具体的错误信息字符串。
# -----------------------------------------------------------------------------


# =============================================================================
# 船舶信息 (ShipInfo) 操作函数
# =============================================================================

def get_all_ships():
    """获取所有船舶信息的列表。"""
    try:
        ships = ShipInfo.objects.all().order_by('mmsi')
        return (True, ships)
    except Exception as e:
        return (False, f"获取船舶列表时发生未知错误: {e}")

def get_ship_by_mmsi(mmsi):
    """根据 MMSI 获取单个船舶信息。"""
    try:
        ship = ShipInfo.objects.get(mmsi=mmsi)
        return (True, ship)
    except ShipInfo.DoesNotExist:
        return (False, f"MMSI为 '{mmsi}' 的船舶不存在。")
    except Exception as e:
        return (False, f"查询船舶时发生未知错误: {e}")

def create_ship(mmsi, ship_name, call_sign, ship_owner):
    """创建一个新的船舶信息。"""
    try:
        with transaction.atomic():
            ship = ShipInfo.objects.create(
                mmsi=mmsi,
                ship_name=ship_name,
                call_sign=call_sign,
                ship_owner=ship_owner
            )
            return (True, ship)
    except IntegrityError:
        return (False, f"创建失败：MMSI号码 '{mmsi}' 或呼号 '{call_sign}' 已存在。")
    except Exception as e:
        return (False, f"创建船舶时发生未知错误: {e}")

def update_ship(mmsi, new_ship_name, new_call_sign, new_ship_owner):
    """更新一个已存在的船舶信息。"""
    try:
        with transaction.atomic():
            ship = ShipInfo.objects.get(mmsi=mmsi)
            ship.ship_name = new_ship_name
            ship.call_sign = new_call_sign
            ship.ship_owner = new_ship_owner
            ship.save()
            return (True, ship)
    except ShipInfo.DoesNotExist:
        return (False, f"更新失败：MMSI为 '{mmsi}' 的船舶不存在。")
    except IntegrityError:
        return (False, f"更新失败：呼号 '{new_call_sign}' 已被其他船舶使用。")
    except Exception as e:
        return (False, f"更新船舶时发生未知错误: {e}")

def delete_ship(mmsi):
    """根据 MMSI 删除一个船舶信息。"""
    try:
        with transaction.atomic():
            ship = ShipInfo.objects.get(mmsi=mmsi)
            ship.delete()
            return (True, f"已成功删除MMSI为 '{mmsi}' 的船舶。")
    except ShipInfo.DoesNotExist:
        return (False, f"删除失败：MMSI为 '{mmsi}' 的船舶不存在。")
    except Exception as e:
        return (False, f"删除船舶时发生未知错误: {e}")

# =============================================================================
# 端站信息 (TerminalInfo) 操作函数
# =============================================================================

def get_all_terminals():
    """获取所有端站信息的列表。"""
    try:
        terminals = TerminalInfo.objects.select_related('ship').all().order_by('sn')
        return (True, terminals)
    except Exception as e:
        return (False, f"获取端站列表时发生未知错误: {e}")

def get_terminal_by_sn(sn):
    """根据 SN 码获取单个端站信息。"""
    try:
        terminal = TerminalInfo.objects.select_related('ship').get(sn=sn)
        return (True, terminal)
    except TerminalInfo.DoesNotExist:
        return (False, f"SN码为 '{sn}' 的端站不存在。")
    except Exception as e:
        return (False, f"查询端站时发生未知错误: {e}")

def create_terminal(sn, ship_mmsi, ip_address=None, port_number=None):
    """创建一个新的端站。"""
    try:
        # 通过 mmsi 获取到 ShipInfo 的实例对象
        ship_instance = ShipInfo.objects.get(mmsi=ship_mmsi)
        
        # 创建 TerminalInfo 对象，并将获取到的 ship_instance 赋值给 ship 字段
        terminal = TerminalInfo.objects.create(
            sn=sn,
            ship=ship_instance,  # 直接传递整个 ship 对象
            ip_address=ip_address,
            port_number=port_number
        )
        return (True, terminal)
    except ShipInfo.DoesNotExist:
        return (False, f"创建失败：mmsi为 '{ship_mmsi}' 的船舶不存在。")
    except IntegrityError:
        return (False, f"创建失败：SN码 '{sn}' 已存在。")
    except Exception as e:
        return (False, f"创建端站时发生未知错误: {e}")

def update_terminal(sn, new_ship_mmsi, new_ip_address=None, new_port_number=None):
    """更新一个已存在的端站信息。"""
    try:
        with transaction.atomic():
            terminal = TerminalInfo.objects.get(sn=sn)
            # 通过 mmsi 查找新的所属船舶
            ship = ShipInfo.objects.get(mmsi=new_ship_mmsi)
            terminal.ship = ship
            terminal.ip_address = new_ip_address
            terminal.port_number = new_port_number
            terminal.save()
            return (True, terminal)
    except TerminalInfo.DoesNotExist:
        return (False, f"更新失败：SN码为 '{sn}' 的端站不存在。")
    except ShipInfo.DoesNotExist:
        return (False, f"更新失败：新的所属船舶MMSI '{new_ship_mmsi}' 不存在。")
    except Exception as e:
        return (False, f"更新端站时发生未知错误: {e}")

def update_terminal_network_info(sn, ip_address, port):
    """
    根据SN码更新端站的网络信息（IP地址和端口号）。
    使用事务以确保操作的原子性。
    """
    try:
        with transaction.atomic():
            # 先获取对象
            terminal = TerminalInfo.objects.get(sn=sn)
            # 再更新字段并保存
            terminal.ip_address = ip_address
            terminal.port_number = port
            terminal.save(update_fields=['ip_address', 'port_number'])
        
        return (True, f"SN '{sn}' 的网络信息已更新为 {ip_address}:{port}。")
    except TerminalInfo.DoesNotExist:
        return (False, f"更新失败：未找到SN为 '{sn}' 的端站。")
    except Exception as e:
        return (False, f"更新SN '{sn}' 的网络信息时发生错误: {e}")

def delete_terminal(sn):
    """根据 SN 码删除一个端站。"""
    try:
        with transaction.atomic():
            terminal = TerminalInfo.objects.get(sn=sn)
            terminal.delete()
            return (True, f"已成功删除SN码为 '{sn}' 的端站。")
    except TerminalInfo.DoesNotExist:
        return (False, f"删除失败：SN码为 '{sn}' 的端站不存在。")
    except Exception as e:
        return (False, f"删除端站时发生未知错误: {e}")

# =============================================================================
# 基站信息 (BaseStationInfo) 操作函数
# =============================================================================

def get_all_base_stations():
    """获取所有基站信息的列表。"""
    try:
        stations = BaseStationInfo.objects.all().order_by('bts_id')
        return (True, stations)
    except Exception as e:
        return (False, f"获取基站列表时发生未知错误: {e}")

def get_base_station_by_id(bts_id):
    """根据基站ID获取单个基站。"""
    try:
        station = BaseStationInfo.objects.get(bts_id=bts_id)
        return (True, station)
    except BaseStationInfo.DoesNotExist:
        return (False, f"ID为 '{bts_id}' 的基站不存在。")
    except Exception as e:
        return (False, f"查询基站时发生未知错误: {e}")
        
def create_base_station(bts_id, bts_name, **kwargs):
    """创建一个新的基站。"""
    try:
        with transaction.atomic():
            station = BaseStationInfo.objects.create(bts_id=bts_id, bts_name=bts_name, **kwargs)
            return (True, station)
    except IntegrityError:
        return (False, f"创建失败：基站ID '{bts_id}' 或基站名称 '{bts_name}' 已存在。")
    except Exception as e:
        return (False, f"创建基站时发生未知错误: {e}")

def update_base_station(bts_id, **kwargs):
    """更新一个已存在的基站信息。"""
    try:
        with transaction.atomic():
            station = BaseStationInfo.objects.get(bts_id=bts_id)
            for key, value in kwargs.items():
                # setattr 是一个动态设置对象属性的方法
                setattr(station, key, value)
            station.save()
            return (True, station)
    except BaseStationInfo.DoesNotExist:
        return (False, f"更新失败：ID为 '{bts_id}' 的基站不存在。")
    except IntegrityError:
        # 如果更新后的 bts_name 与其他记录冲突
        return (False, "更新失败：基站名称与其他记录冲突。")
    except Exception as e:
        return (False, f"更新基站时发生未知错误: {e}")

def delete_base_station(bts_id):
    """根据基站ID删除一个基站。"""
    try:
        with transaction.atomic():
            station = BaseStationInfo.objects.get(bts_id=bts_id)
            station.delete()
            return (True, f"已成功删除ID为 '{bts_id}' 的基站。")
    except BaseStationInfo.DoesNotExist:
        return (False, f"删除失败：ID为 '{bts_id}' 的基站不存在。")
    except Exception as e:
        return (False, f"删除基站时发生未知错误: {e}")

# =============================================================================
# 端站上报信息 (TerminalReport) 操作函数
# =============================================================================

def create_terminal_report(**kwargs):
    """
    创建一个新的端站上报记录。
    由于字段繁多，使用 **kwargs 接收所有字段数据。
    """
    try:
        # 上报信息是日志型数据，单条写入，事务不是必须的，但使用无害
        with transaction.atomic():
            report = TerminalReport.objects.create(**kwargs)
            return (True, report)
    except IntegrityError:
        # 这会捕获违反 unique_together 约束的错误
        return (False, "创建失败：在同一时间点，该设备已有上报记录（type, sn, date, time 组合重复）。")
    except Exception as e:
        return (False, f"创建上报记录时发生未知错误: {e}")

def get_reports_by_sn(sn, limit=100):
    """根据 SN 码查询最新的 N 条上报记录。"""
    try:
        # reports = TerminalReport.objects.filter(sn=sn).order_by('-report_date', '-report_time')[:limit]
        
        reports = TerminalReport.objects.filter(sn=sn).extra(
            order_by=['-report_datetime_generated']
        )[:limit]

        return (True, reports)
    except Exception as e:
        return (False, f"按SN码查询上报记录时发生错误: {e}")

def get_reports_by_date_range(start_date, end_date):
    """根据日期范围查询上报记录。"""
    try:
        # __range 查询操作符用于范围查询
        reports = TerminalReport.objects.filter(report_date__range=(start_date, end_date)).order_by('report_date', 'report_time')
        return (True, reports)
    except Exception as e:
        return (False, f"按日期范围查询上报记录时发生错误: {e}")

def delete_report_by_id(report_id):
    """
    根据记录的自增ID删除一条上报记录。
    (注意：删除历史日志通常是管理员操作，用于数据清理)
    """
    try:
        with transaction.atomic():
            report = TerminalReport.objects.get(id=report_id)
            report.delete()
            return (True, f"已成功删除ID为 '{report_id}' 的上报记录。")
    except TerminalReport.DoesNotExist:
        return (False, f"删除失败：ID为 '{report_id}' 的上报记录不存在。")
    except Exception as e:
        return (False, f"删除上报记录时发生未知错误: {e}")

# =============================================================================
# 端站数据与状态页面 (Antenna) 操作函数
# =============================================================================

def get_latest_report_by_sn(sn):
    """根据 SN 码查询最新的一条上报记录。"""
    # 仅查询，无需使用atomic确保原子性
    try:
        # report = TerminalReport.objects.filter(sn=sn).order_by('-report_date', '-report_time').first()
        
        report = TerminalReport.objects.filter(sn=sn).extra(
            order_by=['-report_datetime_generated']
        ).first()
        
        if report:
            return (True, report)
        else:
            return (True, None) # 即使没有记录，操作本身也是成功的，返回None
    except Exception as e:
        return (False, f"按SN码查询最新上报记录时发生错误: {e}")

# =============================================================================
# GIS 页面相关操作函数
# =============================================================================

def get_reports_by_sn_and_time(sn, start_time, end_time):
    """
    根据船舶MMSI和时间范围，查询该船所有端站的上报记录。
    结果按照上报时间倒序排列 (从新到旧)。
    """
    try:
        # local_start_time = timezone.localtime(start_time)
        # local_end_time = timezone.localtime(end_time)
        # # 由于时间和日期是分开的字段，我们需要构造一个稍微复杂的查询
        # start_date = local_start_time.date()
        # start_t = local_start_time.time()
        # end_date = local_end_time.date()
        # end_t = local_end_time.time()

        # reports = TerminalReport.objects.filter(
        #     sn=sn,
        #     # 日期部分在此范围内
        #     report_date__range=(start_date, end_date)
        # ).exclude(
        #     # 排除掉开始日期里，时间早于开始时间的部分
        #     Q(report_date=start_date, report_time__lt=start_t) |
        #     # 排除掉结束日期里，时间晚于结束时间的部分
        #     Q(report_date=end_date, report_time__gt=end_t)
        # ).order_by('-report_date', '-report_time') # 先按日期降序，再按时间降序

        reports = TerminalReport.objects.filter(sn=sn).extra(
            where=['report_datetime_generated BETWEEN %s AND %s'],
            params=[start_time, end_time]
        ).order_by('-report_datetime_generated') # 按需排序，或 .order_by('report_datetime_generated')
        
        return (True, reports)

    except Exception as e:
        return (False, f"根据sn和时间查询轨迹数据时发生错误: {e}")

def get_latest_report_for_gis_by_sn(sn):
    """
    【为GIS页面新建】根据SN码获取最新的状态上报记录 (返回字典)。
    此函数包含GIS实时更新所需的所有关联信息（MMSI, IP等）。
    """
    try:
        terminal = TerminalInfo.objects.select_related('ship').get(sn=sn)
        ship = terminal.ship
        report_dict = {}

        try:
            # latest_report = TerminalReport.objects.filter(sn=sn).order_by('-report_date', '-report_time').first()
            # 遍历模型的所有字段，将它们添加到字典中

            latest_report = TerminalReport.objects.filter(sn=sn).extra(
                order_by=['-report_datetime_generated']
            ).first()
            
            for field in latest_report._meta.fields:
                report_dict[field.name] = str(getattr(latest_report, field.name))

            # 外键 sn 需要的是字符串值，而不是对象
            # report_dict['sn'] = latest_report.sn.sn 

        except TerminalReport.DoesNotExist:
            gl_logger.info(f"端站 (SN: {sn}) 暂无上报数据，GIS更新将只包含基本信息。")

        # 无论有无上报，都附加必要的关联信息
        # report_dict['sn'] = terminal.sn
        report_dict['ship_name'] = ship.ship_name
        report_dict['mmsi'] = ship.mmsi
        report_dict['ip_address'] = terminal.ip_address
        report_dict['port_number'] = terminal.port_number

        if 'sn' not in report_dict:
            report_dict['sn'] = terminal.sn
        
        return (True, report_dict)
    except TerminalInfo.DoesNotExist:
        return (False, f"SN为 '{sn}' 的端站不存在。")
    except Exception as e:
        return (False, f"为GIS查询最新上报记录时发生错误: {e}")
