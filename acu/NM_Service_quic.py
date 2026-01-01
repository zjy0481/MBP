# -*- coding: utf-8 -*-

# 网管平台的接收与下发 - QUIC版本
# 第二阶段：协议切换（UDP → QUIC）- 保持异步架构，使用QUIC替代UDP

import asyncio
import json
import logging
import uuid
import os
from time import time
from typing import Dict, Any, Optional, Tuple, Set

# Django异步支持
from channels.db import database_sync_to_async

# 第三方库
import redis.asyncio as aioredis
from aioquic.asyncio import serve
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived, ConnectionTerminated
from aioquic.asyncio.protocol import QuicConnectionProtocol

# Django相关
from django.conf import settings
from django.db import models

# 项目内部
from utils import gl_logger
from terminal_management.models import TerminalReport
from terminal_management import services
from channels.layers import get_channel_layer

# QUIC证书配置
DEFAULT_CERT_FILE = "server.crt"  # 服务器证书路径
DEFAULT_KEY_FILE = "server.key"   # 服务器私钥路径
DEFAULT_IP = "192.168.3.28"
DEFAULT_PORT = 59999

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


class NM_QUICProtocol(QuicConnectionProtocol):
    """QUIC协议处理类 - 替换UDP监听"""

    def __init__(self, *args, **kwargs):
        self.service_instance = kwargs.pop('service_instance')
        super().__init__(*args, **kwargs)
        self.client_id = self._quic.host_cid.hex()[:8]
        
        if self.service_instance:
            self.service_instance.register_connection(self.client_id, self)
            gl_logger.info(f"QUIC客户端连接建立: {self.client_id}")

    def quic_event_received(self, event):
        """处理QUIC事件"""
        if isinstance(event, StreamDataReceived):
            try:
                msg_str = event.data.decode('utf-8')
                msg = json.loads(msg_str)
                gl_logger.info(f"QUIC收到客户端 {self.client_id} 消息: {msg}")

                # 使用NM_Service的消息路由逻辑
                if self.service_instance:
                    asyncio.create_task(
                        self.service_instance.route_message_quic(msg, self.client_id)
                    )

            except json.JSONDecodeError:
                gl_logger.error(f"客户端 {self.client_id} 发送非JSON数据")
            except Exception as e:
                gl_logger.error(f"处理客户端 {self.client_id} 消息异常: {e}")

        elif isinstance(event, ConnectionTerminated):
            if self.service_instance:
                self.service_instance.unregister_connection(self.client_id)
            gl_logger.info(f"客户端 {self.client_id} 断开连接: {event.reason_phrase}")

    def send_message(self, msg_dict):
        """通过QUIC向该客户端发送消息"""
        try:
            data = json.dumps(msg_dict).encode('utf-8')
            stream_id = self._quic.get_next_available_stream_id()
            self._quic.send_stream_data(stream_id, data, end_stream=True)
            self.transmit()
            gl_logger.info(f"QUIC向客户端 {self.client_id} 发送: {msg_dict}")
        except Exception as e:
            gl_logger.error(f"QUIC向客户端 {self.client_id} 发送失败: {e}")


class NM_ServiceQUIC:
    """
    NM_Service的QUIC版本
    第二阶段：协议切换（UDP → QUIC），保持异步架构和API兼容
    """
    
    def __init__(self, 
                 host=DEFAULT_IP,
                 port=DEFAULT_PORT,
                 cert_file=DEFAULT_CERT_FILE,
                 key_file=DEFAULT_KEY_FILE):
        self.host = host
        self.port = port
        self.cert_file = cert_file
        self.key_file = key_file
        
        # 异步任务管理
        self.quic_server_task: Optional[asyncio.Task] = None
        self.redis_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        # QUIC连接管理
        self.connections: Dict[str, NM_QUICProtocol] = {}
        self.sn_to_client_id: Dict[str, str] = {}  # SN到client_id的映射
        self.client_id_to_sn: Dict[str, str] = {}  # client_id到SN的映射
        
        # 异步Redis连接
        self.redis_conn: Optional[aioredis.Redis] = None
        self.redis_pubsub: Optional[aioredis.client.PubSub] = None
        
        # 异步锁和请求缓存
        self.pending_requests: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()
        
        # 异步数据库操作
        self.create_terminal_report_async = database_sync_to_async(services.create_terminal_report)
        # self.update_terminal_network_info_async = database_sync_to_async(services.update_terminal_network_info)
        
        # QUIC配置
        self.quic_configuration = self._create_quic_configuration()

    def _create_quic_configuration(self):
        """创建QUIC配置"""
        configuration = QuicConfiguration(
            is_client=False,
            alpn_protocols=["comdi-nm-protocol"],
            idle_timeout=180.0,
        )
        
        # 检查证书文件
        if self.cert_file and self.key_file and os.path.exists(self.cert_file) and os.path.exists(self.key_file):
            configuration.load_cert_chain(self.cert_file, self.key_file)
            gl_logger.info(f"QUIC使用证书文件: {self.cert_file}")
        else:
            # 开发环境使用自签名证书或禁用验证
            configuration.verify_mode = False
            gl_logger.warning("QUIC未找到证书文件，使用开发模式")
            
        return configuration

    def register_connection(self, client_id: str, protocol: NM_QUICProtocol):
        """注册QUIC连接"""
        self.connections[client_id] = protocol
        gl_logger.info(f"QUIC连接注册: {client_id}, 当前连接数: {len(self.connections)}")

    def register_sn_mapping(self, sn: str, client_id: str):
        """注册SN到client_id的映射"""
        self.sn_to_client_id[sn] = client_id
        self.client_id_to_sn[client_id] = sn
        gl_logger.info(f"注册SN映射: SN={sn} -> client_id={client_id}")

    def unregister_connection(self, client_id: str):
        """注销QUIC连接"""
        if client_id in self.connections:
            del self.connections[client_id]
            # 同时清理映射关系
            if client_id in self.client_id_to_sn:
                sn = self.client_id_to_sn.pop(client_id)
                self.sn_to_client_id.pop(sn, None)
                gl_logger.info(f"清理SN映射: SN={sn} -> client_id={client_id}")
            gl_logger.info(f"QUIC连接注销: {client_id}, 当前连接数: {len(self.connections)}")

    async def start(self):
        """启动QUIC版本的NM_Service服务"""
        try:
            self.is_running = True
            
            # 启动异步Redis连接
            await self._start_redis_connection()

            # 启动QUIC服务器
            await self._start_quic_server()

            # 启动Redis监听任务
            self.redis_task = asyncio.create_task(self._redis_loop(), name="Redis_Listener_Task")
            
            gl_logger.info("NM_Service QUIC 所有服务已启动")
            
        except Exception as e:
            gl_logger.error(f"NM_Service QUIC 启动失败: {e}")
            await self.stop()
            raise

    async def stop(self):
        """停止QUIC版本的NM_Service服务"""
        try:
            self.is_running = False
            
            # 取消QUIC服务器任务
            if self.quic_server_task and not self.quic_server_task.done():
                self.quic_server_task.cancel()
                try:
                    await self.quic_server_task
                except asyncio.CancelledError:
                    pass
                    
            # 取消Redis任务
            if self.redis_task and not self.redis_task.done():
                self.redis_task.cancel()
                try:
                    await self.redis_task
                except asyncio.CancelledError:
                    pass
            
            # 关闭Redis连接
            await self._close_redis_connection()
            
            # 关闭所有QUIC连接
            self.connections.clear()
            
            gl_logger.info("NM_Service QUIC 退出")
            
        except Exception as e:
            gl_logger.error(f"NM_Service QUIC 停止时出错: {e}")

    async def _start_quic_server(self):
        """启动QUIC服务器"""
        try:
            self.quic_server_task = asyncio.create_task(
                serve(
                    host=self.host,
                    port=self.port,
                    configuration=self.quic_configuration,
                    create_protocol=lambda *args, **kwargs: NM_QUICProtocol(
                        *args, service_instance=self, **kwargs
                    ),
                ),
                name="QUIC_Server_Task"
            )
            
            # 等待服务器启动
            await self.quic_server_task
            gl_logger.info(f"NM_Service QUIC服务器启动成功，监听 {self.host}:{self.port}")
            
        except Exception as e:
            gl_logger.error(f"NM_Service QUIC服务器启动失败: {e}")
            raise

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
            # 先订阅频道，不传递回调函数
            await self.redis_pubsub.subscribe('udp-command')
            gl_logger.info(f"NM_Service QUIC 已连接到 Redis 并监听 'udp-command' 频道")
        except Exception as e:
            gl_logger.error(f"NM_Service QUIC 连接 Redis 失败: {e}")
            raise

    async def _close_redis_connection(self):
        """关闭异步Redis连接"""
        try:
            if self.redis_pubsub:
                await self.redis_pubsub.close()
            if self.redis_conn:
                await self.redis_conn.close()
        except Exception as e:
            gl_logger.error(f"NM_Service QUIC 关闭Redis连接时出错: {e}")

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
                    gl_logger.error(f"QUIC Redis监听线程出错: {e}")
                    await asyncio.sleep(5)

    async def _handle_redis_message(self, message):
        """处理Redis消息"""
        await self._handle_redis_command(message)

    async def route_message_quic(self, msg_dict: Dict[str, Any], client_id: str):
        """QUIC消息路由分发"""
        request_id = msg_dict.get('request_id')
        
        # 异步检查是否为控制响应
        if request_id:
            async with self.lock:
                if request_id in self.pending_requests:
                    request_info = self.pending_requests.pop(request_id, None)
            
            if request_info:
                await self._handle_control_response(msg_dict, request_info)
                return
        
        # 否则作为上报数据处理
        await self._handle_report_data_quic(msg_dict, client_id)

    async def _handle_report_data_quic(self, msg_dict: Dict[str, Any], client_id: str):
        """QUIC版本处理端站上报数据"""
        try:
            gl_logger.info(f"QUIC收到来自客户端 {client_id} 的上报数据: {msg_dict}")
            
            op = msg_dict.get('op')
            op_sub = msg_dict.get('op_sub')
            long = msg_dict.get('long')
            lat = msg_dict.get('lat')
            sn = msg_dict.get('sn')

            if op == 'report':
                gl_logger.info("QUIC正在处理上报消息...")

                if (long == 0.0 and lat == 0.0):
                    gl_logger.warning(f"QUIC已忽略 long={long}, lat={lat} 的消息（异常的地理坐标）。")
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
                    gl_logger.error(f"QUIC存储上报数据失败 (SN: {msg_dict.get('sn')}): {result}")
                    return
                
                sn = msg_dict.get('sn')
                if sn:
                    # 注册SN到client_id的映射关系
                    self.register_sn_mapping(sn, client_id)
                    gl_logger.info(f"QUIC成功处理SN: {sn} 的上报数据")

                gl_logger.info(f"QUIC成功将来自SN: {msg_dict.get('sn')} 的上报存入数据库。")
                
            elif (sn and not op and not op_sub):
                # QUIC心跳包处理 - 仅维护SN映射，不更新数据库
                self.register_sn_mapping(sn, client_id)
                gl_logger.info(f"QUIC收到心跳包，成功处理SN: {sn} 的映射关系")
            else:
                gl_logger.warning(f"QUIC已忽略 op={op}, op_sub={op_sub} 的消息（非上报消息）。")

        except Exception as e:
            gl_logger.error(f"QUIC收到消息时发生报错 [客户端 {client_id}]: {e}")

    async def _handle_control_response(self, response_data: Dict[str, Any], request_info: Dict[str, Any]):
        """异步处理控制指令响应"""
        reply_channel_group = request_info['reply_channel']
        request_id = response_data.get('request_id')
        gl_logger.info(f"QUIC匹配到请求 {request_id} 的响应，准备通过 Channel Layer 转发至组: {reply_channel_group}")
        
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
        """异步处理Redis控制指令（QUIC版本）- 支持基于SN的client_id映射"""
        try:
            command_data = json.loads(message['data'])
            reply_channel = command_data.get('reply_channel')
            payload = command_data.get('payload')

            request_id = payload.get('request_id')
            if not request_id:
                gl_logger.error("QUIC收到的控制指令缺少 'request_id'，予以忽略。")
                return

            # 从payload中获取SN
            sn = payload.get('sn')
            if not sn:
                gl_logger.error("QUIC收到的控制指令缺少 'sn'，予以忽略。")
                return

            # 通过SN获取对应的client_id
            client_id = self.sn_to_client_id.get(sn)
            if not client_id:
                gl_logger.warning(f"QUIC未找到SN {sn} 对应的client_id映射，可能客户端尚未建立连接或上报数据")
                return

            gl_logger.info(f"QUIC收到Redis指令, SN: {sn}, client_id: {client_id}, 请求ID: {request_id}")
            
            # 异步存储待处理请求
            async with self.lock:
                self.pending_requests[request_id] = {
                    'reply_channel': reply_channel,
                    'timestamp': time()
                }

            # 通过QUIC发送消息到指定客户端
            if client_id in self.connections:
                self.connections[client_id].send_message(payload)
                gl_logger.info(f"QUIC成功转发指令到客户端 {client_id}")
            else:
                gl_logger.warning(f"QUIC未找到客户端 {client_id} 的连接")

        except Exception as e:
            gl_logger.error(f"QUIC处理Redis命令时出错: {e}")

    def set_udp_addr_port(self, ip: str, port: int):
        """设置UDP地址和端口（保持API兼容，但QUIC版本使用不同机制）"""
        gl_logger.info(f"QUIC版本忽略UDP地址设置: {ip}:{port}，使用配置: {self.host}:{self.port}")


# 全局QUIC版本NM_Service实例
nm_service_quic = None

async def get_nm_service_quic():
    """获取全局QUIC版本NM_Service实例"""
    global nm_service_quic
    if nm_service_quic is None:
        nm_service_quic = NM_ServiceQUIC()
    return nm_service_quic

async def start_nm_service_quic():
    """启动全局QUIC版本NM_Service服务"""
    service = await get_nm_service_quic()
    await service.start()
    return service

async def stop_nm_service_quic():
    """停止全局QUIC版本NM_Service服务"""
    global nm_service_quic
    if nm_service_quic:
        await nm_service_quic.stop()
        nm_service_quic = None