# -*- coding: utf-8 -*-

# 网管平台的接收与下发

import os
import sys
import django
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mbp_project.settings') 
django.setup()

from utils import gl_logger
from acu.EventManager import EventManager, Event
# from threading import Thread
import threading
import uuid
from time import sleep, time
from json import loads, dumps, JSONDecodeError
from queue import Queue, Empty
import socket
import time
import signal
import sys

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
        #self.__acu = acu

        self.__udp_socket = None
        # 绑定端口
        # self.__udp_addr = ("192.168.222.5", 58888)
        # self.__udp_addr = ('0.0.0.0', 58888)  # 自动绑定到所有可用接口（0.0.0.0），端口为 58888  todo：发布时修改
        self.__udp_addr = ("127.0.0.1", 58888)

        # UDP 的消息循环，负责监听UDP消息，接收后打包成事件发出
        self.__udp_loop_active = False
        self.__udp_loop_thread = threading.Thread(target=self.__udp_loop)
        # self.__udp_loop_thread.setDaemon(True)

        # 通用事务管理器，主工作线程，收发数据和数据处理
        self.__event_manage = EventManager("NM Event Loop")
        # 注册事件处理回调函数
        self.__event_manage.addEventListener(Event.RECEIVE_NM_DATA, self.__handle_nm_data)
        self.__event_manage.addEventListener(Event.SEND_NM_DATA, self.__send_to_nm)

        # # 用于上报的数据字典
        # self.__update_message = {}

        # # 用于下发请求的请求池
        # self.__pending_requests = {}            # 采用字典作为请求池，键为请求ID
        # self.__pending_lock = threading.Lock()  # 用于保护对字典的访问

    def __del__(self):
        pass

    #
    # 启动ACU服务
    # 输入：无
    # 输出：无
    #
    def start(self):
        # 启动通用事件循环线程
        self.__event_manage.start()

        # 建立udp socket
        self.__udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__udp_socket.setblocking(False)  # 设置为非阻塞模式
        # 绑定udp端口
        self.__udp_socket.bind(self.__udp_addr)

        # 启动UDP监听工作线程
        self.__udp_loop_active = True
        self.__udp_loop_thread.start()
        gl_logger.info("NM_Service UDP监听服务启动")

    #
    # 结束ACU服务
    # 输入：无
    # 输出：无
    #
    def stop(self):
        # 关闭UDP监听线程
        self.__udp_loop_active = False
        if self.__udp_loop_thread:
            self.__udp_loop_thread.join(1.0)
        # 关闭socket
        self.__udp_socket.close()
        # 关闭事件循环
        self.__event_manage.stop()
        gl_logger.info("NM_Service退出")

    #
    # 设置UDP的地址和端口
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
                    peer_ip = addr[0]
                    peer_port = addr[1]
                    self.__recv_from_nm(peer_ip=peer_ip, peer_port=peer_port, msg=data)
            except BlockingIOError:
                # 没有数据时继续循环
                # time.sleep(0.1)
                pass
            except Exception as e:
                if self.__udp_loop_active:
                    gl_logger.error(f"接收错误: {e}")
            finally:
                # 释放cpu
                time.sleep(0.1)

    #
    # 当收到网管发来的消息后，调用该函数构造事件，并加入到事件分发队列
    # 输入：peer_ip, peer_port, msg
    # 输出：无
    #
    def __recv_from_nm(self, peer_ip, peer_port, msg):
        # 构建事件
        ev = Event(Event.RECEIVE_NM_DATA)
        ev.dict={'peer_ip': peer_ip, 'peer_port': peer_port, 'msg': msg}

        # 加入事件循环，分发事件
        self.__event_manage.sendEvent(ev)

    #
    # 事件循环分发的事件处理函数。
    # 输入：事件event
    # 输出：无
    #
    def __handle_nm_data(self, event: Event):
        """
        处理从NM接收到的数据，并将其存入数据库
        """
        peer_ip = event.dict['peer_ip']
        peer_port = event.dict['peer_port']

        raw_data = event.dict['msg']
        data_str = None

        try:
            # 优先尝试使用 UTF-8 解码
            data_str = raw_data.decode('utf-8')
        except UnicodeDecodeError:
            gl_logger.warning(f"使用 UTF-8 解码来自 [{peer_ip}:{peer_port}] 的消息失败，尝试使用 GBK...")
            try:
                # 如果 UTF-8 失败，则回退到使用 GBK 解码
                data_str = raw_data.decode('gbk')
            except Exception as e:
                gl_logger.error(f"使用 UTF-8 和 GBK 解码来自 [{peer_ip}:{peer_port}] 的消息均失败: {e}")
                return # 如果两种主要编码都失败，则放弃处理此消息
            
        try:
            msg_dict = loads(data_str)
            gl_logger.info(f"收到来自 [{peer_ip}:{peer_port}], 消息为： {msg_dict}")

            # 检查收到的是否是一个响应
            response_to_id = msg_dict.get('request_id') 
            if response_to_id:
                # 如果这是一个响应，我们不直接处理它，而是把它封装成一个新的事件。
                # 事件的类型就是请求的ID，这样之前注册的临时监听器就能收到它。
                response_event = Event(type_=response_to_id)
                response_event.dict['response_data'] = msg_dict
                # 将这个响应事件发送给 EventManager
                self.__event_manage.sendEvent(response_event)
                # 响应已被分发，此处的常规处理流程结束
                return
            
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

                report_instance = TerminalReport.objects.create(**model_data)
                gl_logger.info(f"成功将来自SN: {report_instance.sn} 的上报存入数据库。")
            else:
                gl_logger.warning(f"已忽略 op={op}, op_sub={op_sub} 的消息")

        except Exception as e:
            # 捕获所有可能的异常，例如JSON解析错误、数据库写入错误等
            gl_logger.error(f"收到消息时发生报错 [{peer_ip}:{peer_port}]: {e}")

    #
    # 事件循环的分发响应处理函数。
    # 输入：事件event
    # 输出：无
    #
    def __send_to_nm(self, event):
        data = event.dict['msg'].encode('utf-8')    # 编码
        peer_ip = event.dict['peer_ip']
        peer_port = event.dict['peer_port']
        try:
            # udp 发送时必须是二进制串流，所以统一在此方法encode
            # self.__udp_socket.sendto(event.msg.encode('utf-8'), (event.peer_ip, event.peer_port)) # 如果输入的是文字，这里要编码成二进制串
            self.__udp_socket.sendto(data, (peer_ip, peer_port))
            # gl_logger.info(f"发送到 ({peer_ip}:{peer_port}) 消息：{data}")
        except Exception as err:
            gl_logger.error(f"发送到端站({peer_ip}:{peer_port}) 异常：{err} 消息：{data}")

    #
    # 发送数据到指定对端
    # 输入：事件event
    # 输出：无
    #
    def send_to_nm(self, peer_ip, peer_port, msg:str):
        # 构建发送给NM的事件
        ev = Event(Event.SEND_NM_DATA)
        ev.dict={'peer_ip': peer_ip, 'peer_port': peer_port, 'msg': msg}
        # 加入事件循环，分发事件
        self.__event_manage.sendEvent(ev)

    #
    # 发送一个请求并阻塞等待其响应。
    # peer_ip (str): 目标IP，peer_port (int): 目标端口，request_data (dict): 请求的数据字典，服务会自动添加唯一ID，timeout (float): 等待响应的超时时间（秒）
    # 输出：dict or None: 成功则返回响应的数据字典，超时则返回 None。
    #
    def send_request_and_wait(self, peer_ip: str, peer_port: int, request_data: dict, timeout=10.0):
        request_id = str(uuid.uuid4())
        request_data['request_id'] = request_id  # 请求和响应都使用 'request_id' 字段

        # 创建一个临时的队列，用于在线程间同步响应结果
        response_queue = Queue()

        # 定义一个一次性、临时的事件处理函数 (Handler)
        def _on_response_received(event: Event):
            # 从事件中获取响应字典
            response_dict = event.dict.get('response_data') 
            # 将响应数据放入队列，从而唤醒等待的线程
            response_queue.put(response_dict)
            # 处理完后，立即移除这个临时的监听器，防止内存泄漏
            self.__event_manage.removeEventListener(request_id, _on_response_received)

        # 动态地为这个唯一的 request_id 注册事件监听器
        # 我们把 request_id 本身当作一个临时的事件类型 (event.type_)
        self.__event_manage.addEventListener(request_id, _on_response_received)

        try:
            # 正常发送请求数据
            self.send_to_nm(peer_ip, peer_port, dumps(request_data))
            gl_logger.info(f"已发送请求 (ID: {request_id}) 到 {peer_ip}:{peer_port}")

            # 阻塞等待，从队列中获取结果
            try:
                # .get() 方法会阻塞，直到队列中有数据或超时
                response = response_queue.get(block=True, timeout=timeout)
                gl_logger.info(f"已收到请求 (ID: {request_id}) 的响应。")
                return response
            except Empty:
                gl_logger.warning(f"等待请求 (ID: {request_id}) 的响应超时。")
                return None

        finally:
            # 无论成功、失败还是超时，都确保移除监听器
            self.__event_manage.removeEventListener(request_id, _on_response_received)


# 该main函数仅用于测试
if __name__ == '__main__':
    nm = NM_Service()

    nm.start()

    sleep(10)
    msg = "hello world! I'm network management"
    nm.send_to_nm('127.0.0.1', 9999, msg)

    sleep(30)
    print("程序退出")
    nm.stop()