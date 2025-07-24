# terminal_management/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
from .models import TerminalReport

@receiver(post_save, sender=TerminalReport)
def terminal_report_updated(sender, instance, created, **kwargs):
    """
    当TerminalReport模型有新的记录被保存或更新时，此函数被调用。
    """
    print(f"信号触发: TerminalReport (SN: {instance.sn}) 已更新。准备推送...")

    # 准备要发送给前端的数据包
    # 这个数据包的结构应该与前端JS期望的格式一致
    message_to_send = {
        'cmd': 0x35, # 'GET_ADU_UPDATE_INFO' 的值，代表系统信息上报
        'systemState': instance.op_sub, # 我们可以复用字段
        'btsName': instance.bts_name,
        'btsLongitude': instance.bts_long,
        'btsLatitude': instance.bts_lat,
        'longitude': instance.long,
        'latitude': instance.lat,
        'theoryYaw': instance.theory_yaw,
        'yaw': instance.yaw,
        'pitch': instance.pitch,
        'roll': instance.roll,
        'yawLimitState': instance.yao_limit_state,
        'temperature': instance.temp,
        'humidity': instance.humi,
        # ... 其他前端需要的字段 ...
    }

    # 获取Channel Layer实例
    channel_layer = get_channel_layer()

    # 异步地向名为'terminal_updates'的组广播消息
    # 'type'指定了消费者中处理该消息的方法名
    async_to_sync(channel_layer.group_send)(
        "terminal_updates",
        {
            "type": "terminal.report.message",
            "message": message_to_send
        }
    )