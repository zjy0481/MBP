# terminal_management/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

from .models import ShipInfo, TerminalInfo, BaseStationInfo

# 确保 @receiver 的 sender 参数使用正确的类名 ShipInfo
@receiver(post_save, sender=ShipInfo)
def ship_update_handler(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    message = {
        'type': 'ship_update',
        'ship_id': instance.id,
        'name': instance.name,
        'status': instance.status,
    }
    async_to_sync(channel_layer.group_send)(
        'data_updates',
        {
            'type': 'send_update',
            'message': message
        }
    )

# 纠正：确保 @receiver 的 sender 参数使用正确的类名 TerminalInfo
@receiver(post_save, sender=TerminalInfo)
def terminal_update_handler(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    message = {
        'type': 'terminal_update',
        'terminal_id': instance.id,
        'name': instance.name,
    }
    async_to_sync(channel_layer.group_send)(
        'data_updates',
        {'type': 'send_update', 'message': message}
    )

# 确保 @receiver 的 sender 参数使用正确的类名 BaseStationInfo
@receiver(post_save, sender=BaseStationInfo)
def basestation_update_handler(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    message = {
        'type': 'basestation_update',
        'id': instance.id,
        'name': instance.name,
    }
    async_to_sync(channel_layer.group_send)(
        'data_updates',
        {'type': 'send_update', 'message': message}
    )

# 确保 @receiver 的 sender 参数使用正确的类名 ShipInfo
@receiver(post_delete, sender=ShipInfo)
def ship_delete_handler(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    message = {
        'type': 'ship_delete',
        'ship_id': instance.id,
    }
    async_to_sync(channel_layer.group_send)(
        'data_updates',
        {'type': 'send_update', 'message': message}
    )