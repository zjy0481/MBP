# -*- coding: utf-8 -*-

# 网管平台的接收与下发 - 异步版本
# 第一阶段：基础设施准备 - 保持UDP协议，使用异步架构

import asyncio
import json
import logging
import uuid
from time import time
from typing import Dict, Any, Optional, Tuple

# Django异步支持
from channels.db import database_sync_to_async

# 第三方库
import redis.asyncio as aioredis
import socket

# Django相关
from django.conf import settings
from django.db import models

# 项目内部
from utils import gl_logger
from terminal_management.models import TerminalReport
from terminal_management import services
from channels.layers import get_channel_layer

# 定义映射字典（消息字段：数据库字段）- 与原版本保持一致
JSON_TO_MODEL_MAP = {
    # 复合唯一约束字段 (Compound Unique Fields)
    'type': 'type',
    'sn': 'sn',
    'date': 'report_date',
    'time': 'report_time',

    # 操作信息 (Operation Info)
    'op': 'op',
    'op_sub': 'op_sub',

    # 端站状态信息 (Terminal Status)
    'system_state': 'system_stat',
    'wireless_network_state': 'wireless_network_stat',
    'long': 'long',
    'lat': 'lat',
    'theory_yaw': 'theory_yaw',
    'yaw': 'yaw',
    'pitch': 'pitch',
    'roll': 'roll',
    'yao_limit_state': 'yao_limit_state',
    'temp': 'temp',
    'humi': 'humi',

    # 基站相关信息 (Base Station Info)
    'bts_name': 'bts_name',
    'bts_long': 'bts_long',
    'bts_lat': 'bts_lat',
    'bts_no': 'bts_number',
    'bts_group_no': 'bts_group_number',
    'bts_r': 'bts_r',

    # 通信质量信息 (Communication Quality)
    'upstream_rate': 'upstream_rate',
    'downstream_rate': 'downstream_rate',
    'standard': 'standard',
    'plmn': 'plmn',
    'cellid': 'cellid',
    'pci': 'pci',
    'rsrp': 'rsrp',
    'sinr': 'sinr',
    'rssi': 'rssi',
}

class NM_ServiceAsync:
    """
    NM_Service的异步版本
    第一阶段：基础设施准备阶段，保持UDP协议，但使用异步架构
    """
    
    # 缓存区大小
    MAX_BUFFER_LENGTH = 4096

    def __init__(self):
        self.udp_socket: Optional[socket.socket] = None
        # 绑定端口
        self.udp_addr = ("127.0.0.1", 59999)
        
        # 异步任务管理
        self.udp_task: Optional[asyncio.Task] = None
        self.redis_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        # 异步Redis连接
        self.redis_conn: Optional[aioredis.Redis] = None
        self.redis_pubsub: Optional[aioredis.client.PubSub] = None
        
        # 异步锁和请求缓存
        self.pending_requests: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()
        
        # 异步数据库操作
        self.create_terminal_report_async = database_sync_to_async(services.create_terminal_report)
        self.update_terminal_network_info_async = database_sync_to_async(services.update_terminal_network_info)

    async def start(self):
        """启动异步NM_Service服务"""
        try:
            self.is_running = True
            
            # 创建异步UDP socket
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setblocking(False)
            self.udp_socket.bind(self.udp_addr)
            gl_logger.info("NM_Service Async UDP监听服务启动")

            # 启动异步Redis连接
            await self._start_redis_connection()

            # 启动异步任务
            self.udp_task = asyncio.create_task(self._udp_loop(), name="UDP_Receiver_Task")
            self.redis_task = asyncio.create_task(self._redis_loop(), name="Redis_Listener_Task")
            
            gl_logger.info("NM_Service Async 所有服务已启动")
            
        except Exception as e:
            gl_logger.error(f"NM_Service Async 启动失败: {e}")
            await self.stop()
            raise

    async def stop(self):
        """停止异步NM_Service服务"""
        try:
            self.is_running = False
            
            # 取消异步任务
            if self.udp_task and not self.udp_task.done():
                self.udp_task.cancel()
                try:
                    await self.udp_task
                except asyncio.CancelledError:
                    pass
                    
            if self.redis_task and not self.redis_task.done():
                self.redis_task.cancel()
                try:
                    await self.redis_task
                except asyncio.CancelledError:
                    pass
            
            # 关闭UDP socket
            if self.udp_socket:
                self.udp_socket.close()
                
            # 关闭Redis连接
            await self._close_redis_connection()
            
            gl_logger.info("NM_Service Async 退出")
            
        except Exception as e:
            gl_logger.error(f"NM_Service Async 停止时出错: {e}")

    async def _start_redis_connection(self):
        """启动异步Redis连接"""
        try:
            redis_settings = settings.CHANNEL_LAYERS['default']['CONFIG']['hosts'][0]
            self.redis_conn = aioredis.Redis(
                host=redis_settings[0], 
                port=redis_settings[1], 
                decode_responses=True
            )
            self.redis_pubsub = self.redis_conn.pubsub()
            await self.redis_pubsub.subscribe(udp_command=self._handle_redis_command)
            gl_logger.info(f"NM_Service Async 已连接到 Redis 并监听 'udp-command' 频道")
        except Exception as e:
            gl_logger.error(f"NM_Service Async 连接 Redis 失败: {e}")
            raise

    async def _close_redis_connection(self):
        """关闭异步Redis连接"""
        try:
            if self.redis_pubsub:
                await self.redis_pubsub.close()
            if self.redis_conn:
                await self.redis_conn.close()
        except Exception as e:
            gl_logger.error(f"NM_Service Async 关闭Redis连接时出错: {e}")

    async def _udp_loop(self):
        """异步UDP监听循环"""
        while self.is_running:
            try:
                # 使用asyncio进行异步socket操作
                data, addr = await asyncio.get_event_loop().sock_recvfrom(
                    self.udp_socket, self.MAX_BUFFER_LENGTH
                )
                if data:
                    asyncio.create_task(self.route_message(data, addr))
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.is_running:
                    gl_logger.error(f"异步UDP接收错误: {e}")
                    await asyncio.sleep(0.01)

    async def _redis_loop(self):
        """异步Redis监听循环"""
        while self.is_running:
            try:
                if self.redis_pubsub:
                    # 异步获取Redis消息
                    message = await self.redis_pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    )
                    if message:
                        await self._handle_redis_message(message)
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.is_running:
                    gl_logger.error(f"异步Redis监听线程出错: {e}")
                    await asyncio.sleep(5)

    async def _handle_redis_message(self, message):
        """处理Redis消息"""
        if message['type'] == 'message':
            await self._handle_redis_command(message)

    async def route_message(self, raw_data, addr):
        """异步消息路由分发"""
        decoded_data = None
        try:
            # 优先尝试UTF-8解码
            decoded_data = json.loads(raw_data.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            try:
                # 解码失败则尝试GBK
                decoded_data = json.loads(raw_data.decode('gbk'))
            except Exception as e:
                gl_logger.warning(f"异步解码失败，无法解析来自 {addr} 的消息: {e}")
                return

        request_id = decoded_data.get('request_id')
        
        # 异步检查是否为控制响应
        if request_id:
            async with self.lock:
                if request_id in self.pending_requests:
                    request_info = self.pending_requests.pop(request_id, None)
            
            if request_info:
                await self._handle_control_response(decoded_data, request_info)
                return
        
        # 否则作为上报数据处理
        await self._handle_report_data(decoded_data, addr)

    async def _handle_report_data(self, msg_dict, addr):
        """异步处理端站上报数据"""
        peer_ip, peer_port = addr
        
        try:
            gl_logger.info(f"异步收到来自 [{peer_ip}:{peer_port}]的上报数据, 消息为： {msg_dict}")
            
            op = msg_dict.get('op')
            op_sub = msg_dict.get('op_sub')
            long = msg_dict.get('long')
            lat = msg_dict.get('lat')
            sn = msg_dict.get('sn')

            if op == 'report':
                gl_logger.info("异步正在处理上报消息...")

                if (long == 0.0 and lat == 0.0):
                    gl_logger.warning(f"异步已忽略 long={long}, lat={lat} 的消息（异常的地理坐标）。")
                    return

                model_data = {}
                _sentinel = object()

                for msg_key, model_field in JSON_TO_MODEL_MAP.items():
                    value = msg_dict.get(msg_key, _sentinel)
                    if value is not _sentinel:
                        if value == 'N/A':
                            value = None
                        if value is not None and isinstance(TerminalReport._meta.get_field(model_field), (models.CharField, models.TextField)):
                            value = str(value)
                        model_data[model_field] = value

                # 异步数据库操作
                success, result = await self.create_terminal_report_async(**model_data)
                if not success:
                    gl_logger.error(f"异步存储上报数据失败 (SN: {msg_dict.get('sn')}): {result}")
                    return
                
                sn = msg_dict.get('sn')
                if sn:
                    update_success, update_result = await self.update_terminal_network_info_async(sn, peer_ip, peer_port)
                    if not update_success:
                        gl_logger.warning(f"异步更新端站网络信息失败 (SN: {sn}): {update_result}")
                    else:
                        gl_logger.info(f"异步成功更新 SN: {sn} 的网络信息为 {peer_ip}:{peer_port}。")

                gl_logger.info(f"异步成功将来自SN: {msg_dict.get('sn')} 的上报存入数据库。")
                
            elif (sn and not op and not op_sub):
                update_success, update_result = await self.update_terminal_network_info_async(sn, peer_ip, peer_port)
                if not update_success:
                    gl_logger.warning(f"异步更新端站网络信息失败 (SN: {sn}): {update_result}")
                else:
                    gl_logger.info(f"异步收到心跳包，成功更新 SN: {sn} 的网络信息为 {peer_ip}:{peer_port}。")
            else:
                gl_logger.warning(f"异步已忽略 op={op}, op_sub={op_sub} 的消息（非上报消息）。")

        except Exception as e:
            gl_logger.error(f"异步收到消息时发生报错 [{peer_ip}:{peer_port}]: {e}")

    async def _handle_control_response(self, response_data, request_info):
        """异步处理控制指令响应"""
        reply_channel_group = request_info['reply_channel']
        request_id = response_data.get('request_id')
        gl_logger.info(f"异步匹配到请求 {request_id} 的响应，准备通过 Channel Layer 转发至组: {reply_channel_group}")
        
        channel_layer = get_channel_layer()
        if channel_layer:
            await channel_layer.group_send(
                reply_channel_group,
                {
                    "type": "udp.reply",
                    "message": json.dumps(response_data)
                }
            )

    async def _handle_redis_command(self, message):
        """异步处理Redis控制指令"""
        try:
            command_data = json.loads(message['data'])
            ip = command_data.get('ip')
            port = command_data.get('port')
            reply_channel = command_data.get('reply_channel')
            payload = command_data.get('payload')

            request_id = payload.get('request_id')
            if not request_id:
                gl_logger.error("异步收到的控制指令缺少 'request_id'，予以忽略。")
                return

            gl_logger.info(f"异步收到Redis指令, 生成请求, ID: {request_id}, 发往 {ip}:{port}")
            
            request_to_send = json.dumps(payload).encode('utf-8')
            
            # 异步存储待处理请求
            async with self.lock:
                self.pending_requests[request_id] = {
                    'reply_channel': reply_channel,
                    'timestamp': time()
                }

            # 异步发送UDP消息
            await asyncio.get_event_loop().sock_sendto(
                self.udp_socket, request_to_send, (ip, port)
            )

        except Exception as e:
            gl_logger.error(f"异步处理Redis命令时出错: {e}")

    def set_udp_addr_port(self, ip: str, port: int):
        """设置UDP地址和端口（保持API兼容）"""
        self.udp_addr = (ip, port)
        if self.udp_socket:
            self.udp_socket.bind(self.udp_addr)


# 全局异步NM_Service实例
nm_service_async = None

async def get_nm_service_async():
    """获取全局异步NM_Service实例"""
    global nm_service_async
    if nm_service_async is None:
        nm_service_async = NM_ServiceAsync()
    return nm_service_async

async def start_nm_service_async():
    """启动全局异步NM_Service服务"""
    service = await get_nm_service_async()
    await service.start()
    return service

async def stop_nm_service_async():
    """停止全局异步NM_Service服务"""
    global nm_service_async
    if nm_service_async:
        await nm_service_async.stop()
        nm_service_async = None