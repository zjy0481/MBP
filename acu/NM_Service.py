# -*- coding: utf-8 -*-

# 网管平台的接收与下发

# 这些配置仅用于UDP模块的独立测试
# import os
# import sys
# import django
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mbp_project.settings') 
# django.setup()

from utils import gl_logger
from acu.EventManager import EventManager, Event
# from threading import Thread
import threading
import uuid
from time import sleep, time
# from json import loads, dumps, JSONDecodeError
import json
from queue import Queue, Empty
import socket
# import time
# import signal
# import sys
import redis
from django.conf import settings

from django.db import models
from terminal_management.models import TerminalReport   # 引入django生成的端站上报表
from terminal_management import services

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# 定义映射字典（消息字段：数据库字段）
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

class NM_Service():
    # 缓存区大小
    __MAX_BUFFER_LENGTH = 2048

    def __init__(self):
        self.__udp_socket = None
        # 绑定端口
        self.__udp_addr = ("127.0.0.1", 59999)

        # UDP 的消息循环，负责监听UDP消息，接收后打包成事件发出
        self.__udp_loop_active = False
        self.__udp_loop_thread = threading.Thread(target=self.__udp_loop, name="UDP_Receiver_Thread")
        # self.__udp_loop_thread.setDaemon(True)

        # --- Redis 监听部分 ---
        self.__redis_conn = None
        self.__redis_pubsub = None
        self.__redis_loop_active = False
        self.__redis_loop_thread = threading.Thread(target=self.__redis_loop, name="Redis_Listener_Thread")
        
        # 用于存储请求和响应的队列
        self.__pending_requests = {}
        self.__lock = threading.Lock()

    #
    # 启动ACU服务
    # 输入：无
    # 输出：无
    #
    def start(self):
        # 启动通用事件循环线程
        # self.__event_manage.start()

        # 建立udp socket
        self.__udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__udp_socket.setblocking(False)  # 设置为非阻塞模式
        # 绑定udp端口
        self.__udp_socket.bind(self.__udp_addr)

        # 启动UDP监听工作线程
        self.__udp_loop_active = True
        self.__udp_loop_thread.start()
        gl_logger.info("NM_Service UDP监听服务启动")

        # --- 启动 Redis 监听 ---
        try:
            redis_settings = settings.CHANNEL_LAYERS['default']['CONFIG']['hosts'][0]
            self.__redis_conn = redis.Redis(host=redis_settings[0], port=redis_settings[1], decode_responses=True)
            self.__redis_pubsub = self.__redis_conn.pubsub()
            self.__redis_pubsub.subscribe(**{'udp-command': self.__handle_redis_command})
            self.__redis_loop_active = True
            self.__redis_loop_thread.start()
            gl_logger.info(f"NM_Service 已连接到 Redis 并监听 'udp-command' 频道")
        except Exception as e:
            gl_logger.error(f"NM_Service 连接 Redis 失败: {e}")

    #
    # 结束ACU服务
    # 输入：无
    # 输出：无
    #
    def stop(self):
        # 关闭UDP监听线程
        self.__udp_loop_active = False
        if self.__udp_loop_thread.is_alive():
            self.__udp_loop_thread.join(1.0)
        # 关闭socket
        if self.__udp_socket:
            self.__udp_socket.close()
        # 关闭事件循环
        # self.__event_manage.stop()

        # --- 关闭 Redis ---
        self.__redis_loop_active = False
        if self.__redis_pubsub:
            self.__redis_pubsub.close()
        if self.__redis_conn:
            self.__redis_conn.close()
        if self.__redis_loop_thread.is_alive():
            self.__redis_loop_thread.join(1.0)

        gl_logger.info("NM_Service退出")

    #
    # ? 设置UDP的地址和端口，也许用不到
    # 输入：ip, port
    # 输出：无
    #
    def set_udp_addr_port(self, ip:str, port):
        self.__udp_addr = (ip, port)
        # 设置完毕后，重新绑定一下
        self.__udp_socket.bind(self.__udp_addr)

    #
    # UDP线程的核心循环，守候监听客户端发来的消息，并调用处理函数
    # 输入：无
    # 输出：无
    #
    def __udp_loop(self):
        """接收线程主循环"""
        while self.__udp_loop_active:
            try:
                data, addr = self.__udp_socket.recvfrom(self.__MAX_BUFFER_LENGTH)
                if data:
                    # peer_ip = addr[0]
                    # peer_port = addr[1]
                    # self.__recv_from_nm(peer_ip=peer_ip, peer_port=peer_port, msg=data)
                    self.route_message(data, addr)
            except BlockingIOError:
                # 没有数据时继续循环
                sleep(0.01)
            except Exception as e:
                if self.__udp_loop_active:
                    gl_logger.error(f"UDP接收错误: {e}")

    #
    # radis线程的核心循环，守候监听Django发来的消息，并调用处理函数
    # 输入：无
    # 输出：无
    #
    def __redis_loop(self):
        while self.__redis_loop_active:
            try:
                # 这个调用会阻塞，直到有消息或超时
                self.__redis_pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            except Exception as e:
                # 仅当服务不是在主动关闭时，才将此异常记录为错误
                if self.__redis_loop_active:
                    gl_logger.error(f"Redis 监听线程出错: {e}")
                    # 如果发生意外错误，暂停一下避免刷屏
                    sleep(5)

    #
    # 判断收到的消息是上报还是响应，并分发给不同处理器
    # 输入：raw_data, addr（ip+port)
    # 输出：无
    #
    def route_message(self, raw_data, addr):
        decoded_data = None
        try:
            # 优先尝试UTF-8解码
            decoded_data = json.loads(raw_data.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            try:
                # 解码失败则尝试GBK (主要针对上报数据)
                decoded_data = json.loads(raw_data.decode('gbk'))
            except Exception as e:
                gl_logger.warning(f"解码失败，无法解析来自 {addr} 的消息: {e}")
                return

        request_id = decoded_data.get('request_id')
        
        # 先在锁外面对 request_id 进行判断
        if request_id:
            # 仅在需要访问共享资源 __pending_requests 时才加锁
            with self.__lock:
                # 再次检查，确保在等待锁的过程中，该请求没有被其他线程处理
                if request_id in self.__pending_requests:
                    # 从等待字典中弹出请求信息，这意味着这个响应只会被处理一次
                    request_info = self.__pending_requests.pop(request_id, None)
                    # 立即释放锁
                else:
                    request_info = None
            
            # 在锁已经释放的情况下，安全地调用处理函数
            if request_info:
                self.__handle_control_response(decoded_data, request_info)
                return # 处理完毕，直接返回
        
        # 如果不是一个我们正在等待的响应，就作为上报数据处理
        self.__handle_report_data(decoded_data, addr)

    #
    # 处理端站上报，将上报信息存入数据库。
    # 输入：raw_data, addr（ip+port）
    # 输出：无
    #
    def __handle_report_data(self, msg_dict, addr):
        peer_ip, peer_port = addr
            
        try:
            gl_logger.info(f"收到来自 [{peer_ip}:{peer_port}]的上报数据, 消息为： {msg_dict}")
            
            # 检查操作类型，处理 'report' 类型的消息
            op = msg_dict.get('op')
            op_sub = msg_dict.get('op_sub')
            long = msg_dict.get('long')
            lat = msg_dict.get('lat')

            if op == 'report':
                gl_logger.info("正在处理上报消息...")

                if (long == 0.0 and lat == 0.0):
                    gl_logger.warning(f"已忽略 long={long}, lat={lat} 的消息（异常的地理坐标）。")
                    return

                model_data = {}
                _sentinel = object()

                for msg_key, model_field in JSON_TO_MODEL_MAP.items():
                    value = msg_dict.get(msg_key, _sentinel) # 采用get方法避免读None发生错误
                    if value is not _sentinel:
                        if value == 'N/A':  # 将N/A手动转换为None
                            value = None
                        if value is not None and isinstance(TerminalReport._meta.get_field(model_field), (models.CharField, models.TextField)):
                            # 如果models中对应字段类型为CharField，将消息中的值转换为字符串
                            value = str(value)
                        model_data[model_field] = value

                success, result = services.create_terminal_report(**model_data)
                if not success:
                    # 如果存储失败，记录错误并提前返回
                    gl_logger.error(f"存储上报数据失败 (SN: {msg_dict.get('sn')}): {result}")
                    return
                sn = msg_dict.get('sn')
                if sn:
                    update_success, update_result = services.update_terminal_network_info(sn, peer_ip, peer_port)
                    if not update_success:
                        # 如果更新失败，只记录警告，不影响主流程
                        gl_logger.warning(f"更新端站网络信息失败 (SN: {sn}): {update_result}")
                    else:
                        gl_logger.info(f"成功更新 SN: {sn} 的网络信息为 {peer_ip}:{peer_port}。")

                gl_logger.info(f"成功将来自SN: {msg_dict.get('sn')} 的上报存入数据库。")
            else:
                gl_logger.warning(f"已忽略 op={op}, op_sub={op_sub} 的消息（非上报消息）。")

        except Exception as e:
            # 捕获所有可能的异常，例如JSON解析错误、数据库写入错误等
            gl_logger.error(f"收到消息时发生报错 [{peer_ip}:{peer_port}]: {e}")

    def __handle_control_response(self, response_data, request_info):
        """处理精确匹配到的控制指令响应，并通过 Channel Layer 回复"""
        reply_channel_group = request_info['reply_channel']
        request_id = response_data.get('request_id')
        gl_logger.info(f"匹配到请求 {request_id} 的响应，准备通过 Channel Layer 转发至组: {reply_channel_group}")
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            reply_channel_group,
            {
                "type": "udp.reply",
                "message": json.dumps(response_data)
            }
        )

    def __handle_redis_command(self, message):
        """处理从Redis收到的控制指令，发送UDP并等待响应"""
        try:
            command_data = json.loads(message['data'])
            ip = command_data.get('ip')
            port = command_data.get('port')
            reply_channel = command_data.get('reply_channel')
            payload = command_data.get('payload')

            request_id = payload.get('request_id')
            if not request_id:
                gl_logger.error("收到的控制指令缺少 'request_id'，予以忽略。")
                return

            gl_logger.info(f"收到Redis指令, 生成请求, ID: {request_id}, 发往 {ip}:{port}")
            
            request_to_send = json.dumps(payload).encode('utf-8')
            
            # with self.__response_lock:
            #     self.__pending_requests[(ip, port)] = {'reply_channel': reply_channel}

            with self.__lock:
                self.__pending_requests[request_id] = {
                    'reply_channel': reply_channel,
                    'timestamp': time() # todo记录时间戳，可用于清理超时请求
                }

            self.__udp_socket.sendto(request_to_send, (ip, port))

        except Exception as e:
            gl_logger.error(f"处理Redis命令时出错: {e}")

