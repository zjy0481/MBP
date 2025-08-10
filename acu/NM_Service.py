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
import time
import signal
import sys
import redis
from django.conf import settings

from django.db import models
from terminal_management.models import TerminalReport   # 引入django生成的端站上报表

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
        self.__udp_addr = ("127.0.0.1", 58888)

        # UDP 的消息循环，负责监听UDP消息，接收后打包成事件发出
        self.__udp_loop_active = False
        self.__udp_loop_thread = threading.Thread(target=self.__udp_loop)
        # self.__udp_loop_thread.setDaemon(True)

        # 通用事务管理器，主工作线程，收发数据和数据处理
        # self.__event_manage = EventManager("NM Event Loop")
        # 注册事件处理回调函数
        # self.__event_manage.addEventListener(Event.RECEIVE_NM_DATA, self.__handle_nm_data)
        # self.__event_manage.addEventListener(Event.SEND_NM_DATA, self.__send_to_nm)

        # --- Redis 监听部分 ---
        self.__redis_conn = None
        self.__redis_pubsub = None
        self.__redis_loop_active = False
        self.__redis_loop_thread = threading.Thread(target=self.__redis_loop, name="Redis_Listener_Thread")
        
        # 用于存储请求和响应的队列
        self.__pending_requests = {}
        self.__response_lock = threading.Lock()

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
                # time.sleep(0.1)
                pass
            except Exception as e:
                if self.__udp_loop_active:
                    gl_logger.error(f"UDP接收错误: {e}")
            finally:
                # 释放cpu
                time.sleep(0.01)

    #
    # radis线程的核心循环，守候监听Django发来的消息，并调用处理函数
    # 输入：无
    # 输出：无
    #
    def __redis_loop(self):
        while self.__redis_loop_active:
            try:
                self.__redis_pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            except Exception as e:
                gl_logger.error(f"Redis 监听线程出错: {e}")
                time.sleep(5)

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
        
        with self.__lock:
            if request_id and request_id in self.__pending_requests:
                # 如果有 request_id 且在等待列表中，则为响应
                self.__handle_request_response(decoded_data, request_id)
            else:
                # 否则为上报
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

            if op == 'report':
                gl_logger.info("正在处理上报消息...")

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

                TerminalReport.objects.create(**model_data)
                gl_logger.info(f"成功将来自SN: {msg_dict.get('sn')} 的上报存入数据库。")
            else:
                gl_logger.warning(f"已忽略 op={op}, op_sub={op_sub} 的消息（非上报消息）。")

        except Exception as e:
            # 捕获所有可能的异常，例如JSON解析错误、数据库写入错误等
            gl_logger.error(f"收到消息时发生报错 [{peer_ip}:{peer_port}]: {e}")

    # #
    # # 事件循环的分发响应处理函数。
    # # 输入：事件event
    # # 输出：无
    # #
    # def __send_to_nm(self, event):
    #     data = event.dict['msg'].encode('utf-8')    # 编码
    #     peer_ip = event.dict['peer_ip']
    #     peer_port = event.dict['peer_port']
    #     try:
    #         # udp 发送时必须是二进制串流，所以统一在此方法encode
    #         # self.__udp_socket.sendto(event.msg.encode('utf-8'), (event.peer_ip, event.peer_port)) # 如果输入的是文字，这里要编码成二进制串
    #         self.__udp_socket.sendto(data, (peer_ip, peer_port))
    #         # gl_logger.info(f"发送到 ({peer_ip}:{peer_port}) 消息：{data}")
    #     except Exception as err:
    #         gl_logger.error(f"发送到端站({peer_ip}:{peer_port}) 异常：{err} 消息：{data}")

    # #
    # # 发送数据到指定对端
    # # 输入：事件event
    # # 输出：无
    # #
    # def send_to_nm(self, peer_ip, peer_port, msg:str):
    #     # 构建发送给NM的事件
    #     ev = Event(Event.SEND_NM_DATA)
    #     ev.dict={'peer_ip': peer_ip, 'peer_port': peer_port, 'msg': msg}
    #     # 加入事件循环，分发事件
    #     self.__event_manage.sendEvent(ev)

    # #
    # # 发送一个请求并阻塞等待其响应。
    # # peer_ip (str): 目标IP，peer_port (int): 目标端口，request_data (dict): 请求的数据字典，服务会自动添加唯一ID，timeout (float): 等待响应的超时时间（秒）
    # # 输出：dict or None: 成功则返回响应的数据字典，超时则返回 None。
    # #
    # def send_request_and_wait(self, peer_ip: str, peer_port: int, request_data: dict, timeout=10.0):
    #     request_id = str(uuid.uuid4())
    #     request_data['request_id'] = request_id  # 请求和响应都使用 'request_id' 字段

    #     # 创建一个临时的队列，用于在线程间同步响应结果
    #     response_queue = Queue()

    #     # 定义一个一次性、临时的事件处理函数 (Handler)
    #     def _on_response_received(event: Event):
    #         # 从事件中获取响应字典
    #         response_dict = event.dict.get('response_data') 
    #         # 将响应数据放入队列，从而唤醒等待的线程
    #         response_queue.put(response_dict)
    #         # 处理完后，立即移除这个临时的监听器，防止内存泄漏
    #         self.__event_manage.removeEventListener(request_id, _on_response_received)

    #     # 动态地为这个唯一的 request_id 注册事件监听器
    #     # 我们把 request_id 本身当作一个临时的事件类型 (event.type_)
    #     self.__event_manage.addEventListener(request_id, _on_response_received)

    #     try:
    #         # 正常发送请求数据
    #         self.send_to_nm(peer_ip, peer_port, json.dumps(request_data))
    #         gl_logger.info(f"已发送请求 (ID: {request_id}) 到 {peer_ip}:{peer_port}")

    #         # 阻塞等待，从队列中获取结果
    #         try:
    #             # .get() 方法会阻塞，直到队列中有数据或超时
    #             response = response_queue.get(block=True, timeout=timeout)
    #             gl_logger.info(f"已收到请求 (ID: {request_id}) 的响应。")
    #             return response
    #         except Empty:
    #             gl_logger.warning(f"等待请求 (ID: {request_id}) 的响应超时。")
    #             return None

    #     finally:
    #         # 无论成功、失败还是超时，都确保移除监听器
    #         self.__event_manage.removeEventListener(request_id, _on_response_received)

    def __handle_request_response(self, response_data, request_id):
        """处理精确匹配到的控制指令响应"""
        with self.__lock:
            request_info = self.__pending_requests.pop(request_id, None)
        
        if request_info:
            gl_logger.info(f"匹配到请求 {request_id} 的响应，准备转发至频道: {request_info['reply_channel']}")
            # 将响应通过Redis发回到指定的回复频道
            self.__redis_conn.publish(request_info['reply_channel'], json.dumps(response_data))
        else:
            # 这种情况很少见，可能意味着响应延迟太高，consumer端已经超时放弃了
            gl_logger.warning(f"收到一个已超时的请求 {request_id} 的响应，予以忽略。")


    def __handle_redis_command(self, message):
        """处理从Redis收到的控制指令，发送UDP并等待响应"""
        try:
            command_data = json.loads(message['data'])
            ip = command_data.get('ip')
            port = command_data.get('port')
            reply_channel = command_data.get('reply_channel')
            payload = command_data.get('payload')

            request_id = str(uuid.uuid4())
            payload['request_id'] = request_id

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

