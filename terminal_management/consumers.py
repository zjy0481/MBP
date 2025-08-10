# terminal_management/consumers.py

import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from .services import get_latest_report_by_sn
from utils import gl_logger

from acu.NM_Service import NM_Service
import asyncio

class DataConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'data_updates'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        gl_logger.info(f"WebSocket 链接已建立: {self.channel_name}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        gl_logger.info(f"WebSocket 链接已关闭: {self.channel_name} with code {close_code}")

    # 从前端接收消息
    async def receive(self, text_data):
        gl_logger.info(f"接收到前端消息: {text_data}")
        data = json.loads(text_data)
        message_type = data.get('type')

        # 使用 asyncio.create_task 在后台执行任务，避免阻塞 receive 方法
        if message_type == 'get_latest_report':
            asyncio.create_task(self.handle_get_latest_report(data))
        elif message_type == 'control_command':
            asyncio.create_task(self.handle_control_command(data))
        else:
            gl_logger.warning(f"接收到前端的未知类型消息，类型为: {message_type}")
        
    # 专门处理获取最新上报数据的请求
    async def handle_get_latest_report(self, data):
        sn = data.get('sn')
        if not sn:
            gl_logger.error("在获取最新上报数据时，缺少SN参数")
            return
            
        gl_logger.info(f"正在获取最新上报数据， SN: {sn}")
        try:
            # 使用 database_sync_to_async 将同步的数据库操作转换为异步可调用对象
            db_query = database_sync_to_async(get_latest_report_by_sn)
            success, report = await db_query(sn=sn)

            response_data = None
            if success and report:
                gl_logger.info(f"成功获取了端站（ SN: {sn} ）的最新上报数据")
                # 将模型实例安全地转换为字典
                response_data = {
                    field.name: str(getattr(report, field.name))
                    for field in report._meta.fields
                }
            elif success:
                gl_logger.info(f"数据库查询成功，但端站（ SN: {sn} ）没有历史上报数据")
            else:
                gl_logger.error(f"数据库查询端站数据失败， SN: {sn}， Error: {report}")

            # 将结果发回给客户端
            await self.send_to_client('latest_report_data', {'sn': sn, 'data': response_data})
        except Exception as e:
            gl_logger.error(f"在获取最新上报数据时发生错误 SN {sn}: {e}", exc_info=True)

    async def handle_control_command(self, data):
        """专门处理控制指令"""
        module = data.get('module')
        gl_logger.info(f"Processing 'control_command' for module: {module}")
        
        reply_channel_name = f"udp-reply-{uuid.uuid4().hex}"
        try:
            await self.channel_layer.group_add(reply_channel_name, self.channel_name)

            command_to_send = {
                "ip": data.get('ip'), "port": int(data.get('port')),
                "reply_channel": reply_channel_name, "payload": data.get('payload', {})
            }

            # 通过Redis将命令发送到'udp-command'频道
            await self.channel_layer.send("udp-command", {
                "type": "udp.message",
                "message": json.dumps(command_to_send)
            })

            # 等待回复，设置超时
            event = await asyncio.wait_for(
                self.channel_layer.receive_from_channel(reply_channel_name),
                timeout=5.0
            )
            response_dict = json.loads(event['message'])
            await self.send_to_client('control_response', {
                'module': module, 'success': True,
                'data': response_dict, 'error': None
            })

        except asyncio.TimeoutError:
            gl_logger.warning(f"Control command for module '{module}' timed out.")
            await self.send_to_client('control_response', {
                'module': module, 'success': False,
                'data': None, 'error': "操作失败：端站无响应（超时）。"
            })
        except Exception as e:
            gl_logger.error(f"Exception in handle_control_command for module {module}: {e}", exc_info=True)
            await self.send_to_client('control_response', {
                'module': module, 'success': False,
                'data': None, 'error': "服务器内部错误。"
            })
        finally:
            await self.channel_layer.group_discard(reply_channel_name, self.channel_name)

    # 封装一个向客户端发送消息的辅助函数
    async def send_to_client(self, msg_type, data):
        message_to_send = {'message': {'type': msg_type, **data}}
        gl_logger.info(f"Sending message to client: {json.dumps(message_to_send)}")
        await self.send(text_data=json.dumps(message_to_send))

    # 从 channel layer 接收广播消息并推送给前端
    async def send_update(self, event):
        message = event['message']
        await self.send(text_data=json.dumps(message))

    async def udp_message(self, event):
        await self.channel_layer.send(event['reply_channel'], {
            "type": "redis.reply",
            "message": event['message']
        })

    async def redis_reply(self, event):
        pass