# terminal_management/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

from .models import ShipInfo, TerminalInfo, BaseStationInfo, TerminalReport


# =============================================================================
# 数据库基本表操作函数
# =============================================================================
# --- 更新信号处理器（包括修改与新建） ---

@receiver(post_save, sender=ShipInfo)
def ship_update_handler(sender, instance, **kwargs):
    """
    当 船舶信息 被保存后，发送 WebSocket 消息。
    """
    channel_layer = get_channel_layer()
    message = {
        'type': 'ship_update',
        'mmsi': instance.mmsi,
        'ship_name': instance.ship_name,
        'call_sign': instance.call_sign,
        'ship_owner': instance.ship_owner
    }
    async_to_sync(channel_layer.group_send)(
        'data_updates',
        {'type': 'send_update', 'message': message}
    )

@receiver(post_save, sender=TerminalInfo)
def terminal_update_handler(sender, instance, **kwargs):
    """
    当 端站信息 被保存后，发送 WebSocket 消息。
    """
    channel_layer = get_channel_layer()
    message = {
        'type': 'terminal_update',
        'sn': instance.sn,
        'ship_mmsi': instance.ship.mmsi,
        'ship_name': instance.ship.ship_name,
        'ip_address': instance.ip_address,
        'port_number': instance.port_number
    }
    async_to_sync(channel_layer.group_send)(
        'data_updates',
        {'type': 'send_update', 'message': message}
    )

@receiver(post_save, sender=BaseStationInfo)
def basestation_update_handler(sender, instance, **kwargs):
    """
    当 基站信息 被保存后，发送 WebSocket 消息。
    """
    channel_layer = get_channel_layer()
    message = {
        'type': 'basestation_update',
        'bts_id': instance.bts_id,
        'bts_name': instance.bts_name,
        'longitude': instance.longitude,
        'latitude': instance.latitude
    }
    async_to_sync(channel_layer.group_send)(
        'data_updates',
        {'type': 'send_update', 'message': message}
    )

# --- 删除信号处理器 ---

@receiver(post_delete, sender=ShipInfo)
def ship_delete_handler(sender, instance, **kwargs):
    """
    当 船舶信息 被删除后，发送 WebSocket 消息。
    """
    channel_layer = get_channel_layer()
    message = {
        'type': 'ship_delete',
        'mmsi': instance.mmsi,
    }
    async_to_sync(channel_layer.group_send)(
        'data_updates',
        {'type': 'send_update', 'message': message}
    )

@receiver(post_delete, sender=TerminalInfo)
def terminal_delete_handler(sender, instance, **kwargs):
    """
    当 端站信息 被删除后，发送 WebSocket 消息。
    """
    channel_layer = get_channel_layer()
    message = {
        'type': 'terminal_delete',
        'sn': instance.sn,
    }
    async_to_sync(channel_layer.group_send)(
        'data_updates',
        {'type': 'send_update', 'message': message}
    )

@receiver(post_delete, sender=BaseStationInfo)
def basestation_delete_handler(sender, instance, **kwargs):
    """
    当 基站信息 被删除后，发送 WebSocket 消息。
    """
    channel_layer = get_channel_layer()
    message = {
        'type': 'basestation_delete',
        'bts_id': instance.bts_id,
    }
    async_to_sync(channel_layer.group_send)(
        'data_updates',
        {'type': 'send_update', 'message': message}
    )

# =============================================================================
# antenna——端站数据与状态相关函数
# =============================================================================
# --- 端站数据更新处理器 ---

@receiver(post_save, sender=TerminalReport)
def terminal_report_handler(sender, instance, **kwargs):
    """
    当新的 端站上报信息 被保存后，发送 WebSocket 消息。
    这个信号是“端站数据与状态”页面实时更新的核心。
    """
    channel_layer = get_channel_layer()
    
    # 准备要发送的数据 (将模型实例转换为字典)
    report_data = {
        'type': instance.type, 'sn': instance.sn, 'report_date': str(instance.report_date),
        'report_time': str(instance.report_time), 'op': instance.op, 'op_sub': instance.op_sub,
        'long': instance.long, 'lat': instance.lat, 'theory_yaw': instance.theory_yaw,
        'yaw': instance.yaw, 'pitch': instance.pitch, 'roll': instance.roll,
        'yao_limit_state': instance.yao_limit_state, 'temp': instance.temp, 'humi': instance.humi,
        'bts_name': instance.bts_name, 'bts_long': instance.bts_long, 'bts_lat': instance.bts_lat,
        'bts_number': instance.bts_number, 'bts_group_number': instance.bts_group_number,
        'bts_r': instance.bts_r, 'upstream_rate': instance.upstream_rate,
        'downstream_rate': instance.downstream_rate, 'standard': instance.standard,
        'plmn': instance.plmn, 'cellid': instance.cellid, 'pci': instance.pci,
        'rsrp': instance.rsrp, 'sinr': instance.sinr, 'rssi': instance.rssi,
        'system_stat': instance.system_stat, "wireless_network_stat": instance.wireless_network_stat,
    }

    # 封装成前端可识别的格式
    message = {
        'type': 'latest_report_data', # 与JS端获取最新数据时使用的类型一致
        'sn': instance.sn,
        'data': report_data
    }

    # 向组内广播消息
    async_to_sync(channel_layer.group_send)(
        'data_updates',
        # 注意，这里的'type'是 'send_update', 它会调用 consumer 中的 send_update 方法
        {'type': 'send_update', 'message': message}
    )