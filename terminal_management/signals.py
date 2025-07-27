# terminal_management/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

from .models import ShipInfo, TerminalInfo, BaseStationInfo

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