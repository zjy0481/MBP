# terminal_management/consumers.py

import json
import uuid
import redis
from django.conf import settings
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .services import get_latest_report_by_sn, get_latest_report_for_gis_by_sn
from utils import gl_logger

import asyncio

# --- 创建一个专用于发布的、标准的 Redis 连接 ---
try:
    redis_settings = settings.CHANNEL_LAYERS['default']['CONFIG']['hosts'][0]
    # decode_responses=True 确保我们发布的和接收的都是字符串，而不是字节
    redis_publisher = redis.Redis(host=redis_settings[0], port=redis_settings[1], decode_responses=True)
    gl_logger.info("Consumer: 已成功连接到 Redis 用于发布控制指令。")
except Exception as e:
    redis_publisher = None
    gl_logger.error(f"Consumer: 连接到 Redis 失败，控制功能将不可用: {e}")

class DataConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'data_updates'
        # 初始化一个集合用于追踪后台任务
        self.background_tasks = set()

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        self.pending_replies = {}   # 用于存放等待中请求的 Future 对象，键为request_id
        await self.accept()
        gl_logger.info(f"WebSocket 链接已建立: {self.channel_name}")

    async def disconnect(self, close_code):
        # 在断开连接时，取消所有正在运行的后台任务
        for task in self.background_tasks:
            task.cancel()

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
        task = None

        # 使用 asyncio.create_task 在后台执行任务，避免阻塞 receive 方法
        if message_type == 'get_latest_report':
            task = asyncio.create_task(self.handle_get_latest_report(data))
        elif message_type == 'control_command':
            task = asyncio.create_task(self.handle_control_command(data))
        else:
            gl_logger.warning(f"接收到前端的未知类型消息，类型为: {message_type}")
        
        # 将新创建的任务添加到追踪集合中，并设置完成后的清理回调
        if task:
            self.background_tasks.add(task)
            task.add_done_callback(self.background_tasks.discard)

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
            # gl_logger.info(f"handle_get_latest_report: 查询到状态 {str(getattr(report, "system_stat"))}, {str(getattr(report, "wireless_network_stat"))}")

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
        sn = data.get('sn')
        gl_logger.info(f"正在处理控制指令，模块: {module}")

        # 检查 Redis 连接是否存在
        if not redis_publisher:
            gl_logger.error("无法处理控制指令：Redis 连接不可用。")
            await self.send_to_client('control_response', {
                'module': module, 'success': False,
                'data': None, 'error': "服务器内部错误：无法连接到后端服务。"
            })
            return
        
        # 在这里生成 request_id
        request_id = str(uuid.uuid4())
        future = asyncio.get_running_loop().create_future()
        self.pending_replies[request_id] = future
        reply_channel_name = f"udp-reply-{request_id}"

        try:
            await self.channel_layer.group_add(reply_channel_name, self.channel_name)

            frontend_payload = data.get('payload', {})
            payload = {
                "sn": sn,
                "request_id": request_id  # 将我们的内部ID注入payload
            }

            # --- 根据通信协议设置 payload 包（NM下发） ---
            if module == 'query_work_mode':                         # 查询工作模式
                payload['op'] = 'query'
                payload['op_sub'] = 'work_pattern'

            elif module == 'set_work_mode':                         # 设置工作模式
                payload['op'] = 'antenna_control'
                payload['op_sub'] = 'work_pattern'
                payload['pattern'] = frontend_payload.get('pattern')

            elif module == 'query_device_status':                   # 查询设备状态
                payload['op'] = 'query'
                payload['op_sub'] = 'equipment_status'

            elif module == 'turn_control':                          # 手动控制天线旋转
                payload['op'] = 'antenna_control'
                payload['op_sub'] = 'rotate'
                payload['mode'] = frontend_payload.get('mode')
                payload['axis'] = frontend_payload.get('axis')
                payload['direct'] = frontend_payload.get('direct')
                payload['angle'] = frontend_payload.get('angle')

            elif module == 'adu_rst':                               # 系统复位
                payload['op'] = 'antenna_control'
                payload['op_sub'] = 'adu_rst'
                payload['rst_type'] = frontend_payload.get('rst_type')

            elif module == 'query_rtc':                             # 查询RTC时间
                payload['op'] = 'query'
                payload['op_sub'] = 'RTC'

            elif module == 'set_rtc':                               # 设置RTC时间
                payload['op'] = 'antenna_control'
                payload['op_sub'] = 'set_RTC'
                payload['date'] = frontend_payload.get('date')
                payload['time'] = frontend_payload.get('time')
            
            elif module == 'query_report_config':                   # 查询上报配置
                payload['op'] = 'query'
                payload['op_sub'] = 'report_config'

            elif module == 'set_report_config':                     # 设置上报配置
                payload['op'] = 'antenna_control'
                payload['op_sub'] = 'set_report_config'
                payload['ip'] = frontend_payload.get('ip')
                payload['port'] = frontend_payload.get('port')
                payload['mode'] = frontend_payload.get('mode')
                payload['interval'] = frontend_payload.get('interval')

            elif module == 'query_version':                         # 版本查询
                payload['op'] = 'query'
                payload['op_sub'] = 'version'

            elif module == 'upload_update_file':  # ADU/ACU 文件上传
                payload['op'] = 'update'
                payload['op_sub'] = 'upload_update_file'
                payload['update_type'] = frontend_payload.get('update_type')
                payload['content'] = frontend_payload.get('content')
                payload['file_name'] = frontend_payload.get('file_name')
                
            elif module == 'software_update':                       # ADU/ACU 软件升级
                payload['op'] = 'update'
                payload['op_sub'] = 'software_update'
                payload['update_type'] = frontend_payload.get('update_type')
                payload['file_name'] = frontend_payload.get('file_name')

            elif module == 'station_import':                        # 基站导入
                payload['op'] = 'update'
                payload['op_sub'] = 'base_station_import'
                payload['station_list'] = frontend_payload.get('station_list')

            elif module == 'query_station':                         # 查询基站信息
                payload['op'] = 'query'
                payload['op_sub'] = 'base_station'

            else:                                                   # default
                gl_logger.error(f"收到了一个未知的控制模块: {module}")
                raise ValueError("未知的控制模块")

            command_to_send = {
                "ip": data.get('ip'),
                "port": int(data.get('port')),
                "reply_channel": reply_channel_name,
                "payload": payload
            }

            redis_publisher.publish("udp-command", json.dumps(command_to_send))
            gl_logger.info(f"已向 Redis 'udp-command' 频道发布指令: {command_to_send}")

            # 等待 Future 被设置结果，设置10秒超时，对于更新功能设置60秒超时
            timeout = 60.0 if module in ['update_adu', 'update_acu'] else 10.0
            
            response_dict = await asyncio.wait_for(future, timeout=timeout)
            
            await self.send_to_client('control_response', {
                'module': module, 'success': True,
                'data': response_dict, 'error': None
            })

        except asyncio.TimeoutError:
            gl_logger.warning(f"控制指令 '{module}' 超时。")
            await self.send_to_client('control_response', {
                'module': module, 'success': False,
                'data': None, 'error': "操作失败：端站无响应（超时）。"
            })
        except asyncio.CancelledError:
            gl_logger.info(f"控制指令 '{module}' 因连接关闭而被取消。")
            # 此处无需向客户端发送消息，因为它已经断开了
        except Exception as e:
            gl_logger.error(f"处理控制指令 '{module}' 时发生异常: {e}", exc_info=True)
            await self.send_to_client('control_response', {
                'module': module, 'success': False,
                'data': None, 'error': "服务器内部错误。"
            })
        finally:
            self.pending_replies.pop(request_id, None)
            await self.channel_layer.group_discard(reply_channel_name, self.channel_name)

    # 用于接收 NM_Service 回复的处理器
    async def udp_reply(self, event):
        message_str = event['message']
        gl_logger.info(f"收到来自 NM_Service 的UDP回复: {message_str}")
        
        response_data = json.loads(message_str)
        # 使用 request_id 来查找 future
        request_id = response_data.get('request_id')
        
        future = self.pending_replies.get(request_id)
        if future and not future.done():
            future.set_result(response_data)
        else:
            gl_logger.warning(f"收到了一个未知或已超时的请求的回复, request_id: {request_id}")


    # 封装一个向客户端发送消息的辅助函数
    async def send_to_client(self, msg_type, data):
        message_to_send = {'message': {'type': msg_type, **data}}
        gl_logger.info(f"Sending message to client: {json.dumps(message_to_send)}")
        await self.send(text_data=json.dumps(message_to_send))

    # 从 channel layer 接收广播消息并推送给前端
    async def send_update(self, event):
        """
        接收来自signals的广播。
        1. 转发旧格式消息给 antenna 等页面。
        2. 获取并发送新格式的GIS专属消息。
        """

        original_message = event['message']
        sn = original_message.get('sn')
        if not sn:
            return
        
        # 1. 转发与之前完全兼容的消息，供 antenna 等页面使用
        success, antenna_report = await database_sync_to_async(get_latest_report_by_sn)(sn=sn)
        antenna_report_dict = {}
        for field in antenna_report._meta.fields:
            antenna_report_dict[field.name] = str(getattr(antenna_report, field.name))
            
        await self.send(text_data=json.dumps({'message': original_message}))
        if success:
            # 构造antenna专属的新消息
            message_for_antenna = {
                'type': 'latest_report_data', # 使用新的、专属的类型
                'data': antenna_report_dict
            }
            gl_logger.info(f"正在向antenna页面发送广播更新: {json.dumps({'message': message_for_antenna})}")
            # 直接发送，不经过 send_to_client 的额外包装
            await self.send(text_data=json.dumps({'message': message_for_antenna}))
        else:
            gl_logger.warning(f"send_update 中为GIS获取数据失败 (SN: {sn}): {antenna_report_dict}")


        # 2. 调用为GIS准备的service函数，获取包含MMSI等信息的丰富字典
        success, gis_report_dict = await database_sync_to_async(get_latest_report_for_gis_by_sn)(sn)
        
        if success:
            # 构造GIS专属的新消息
            message_for_gis = {
                'type': 'gis_update_data', # 使用新的、专属的类型
                'data': gis_report_dict
            }
            gl_logger.info(f"正在向GIS页面发送专属广播更新: {json.dumps({'message': message_for_gis})}")
            # 直接发送，不经过 send_to_client 的额外包装
            await self.send(text_data=json.dumps({'message': message_for_gis}))
        else:
            gl_logger.warning(f"send_update 中为GIS获取数据失败 (SN: {sn}): {gis_report_dict}")

    async def udp_message(self, event):
        await self.channel_layer.send(event['reply_channel'], {
            "type": "redis.reply",
            "message": event['message']
        })

    async def redis_reply(self, event):
        pass