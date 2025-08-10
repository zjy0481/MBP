# -*- coding: utf-8 -*-
"""
Created on Tue Nov 13 13:51:31 2018

@author: awing
"""
# 系统模块
from queue import Queue, Empty
from threading import *

########################################################################
class EventManager:
    # ----------------------------------------------------------------------
    def __init__(self, name="Event Loop"):
        """初始化事件管理器"""
        # 事件对象列表
        self.__eventQueue = Queue()
        # 事件管理器开关
        self.__active = False
        # 事件处理线程
        self.__thread = Thread(target=self.__run)
        self.__thread.setName(name)
        # self.count = 0
        # 这里的__handlers是一个字典，用来保存对应的事件的响应函数
        # 其中每个键对应的值是一个列表，列表中保存了对该事件监听的响应函数，一对多
        self.__handlers = {}


    # ----------------------------------------------------------------------
    def __run(self):
        """引擎运行"""
        while self.__active == True:
            try:
                # 获取事件的阻塞时间设为1秒
                event = self.__eventQueue.get(block=True, timeout=1)
                self.__eventProcess(event)
            except Empty:
                pass

    # ----------------------------------------------------------------------
    def __eventProcess(self, event):
        """处理事件"""
        # 检查是否存在对该事件进行监听的处理函数
        if event.type_ in self.__handlers:
            # 若存在，则按顺序将事件传递给处理函数执行
            for handler in self.__handlers[event.type_]:
                handler(event)

    # ----------------------------------------------------------------------
    def start(self):
        """启动"""
        # 将事件管理器设为启动
        self.__active = True
        # 启动事件处理线程
        self.__thread.start()

    # ----------------------------------------------------------------------
    def stop(self):
        """停止"""
        # 将事件管理器设为停止
        self.__active = False
        # 等待事件处理线程退出
        self.__thread.join()

    # ----------------------------------------------------------------------
    def addEventListener(self, type_, handler):
        """绑定事件和监听器处理函数"""
        # 尝试获取该事件类型对应的处理函数列表，若无则创建
        try:
            handlerList = self.__handlers[type_]
        except KeyError:
            handlerList = []
            self.__handlers[type_] = handlerList
        # 若要注册的处理器不在该事件的处理器列表中，则注册该事件
        if handler not in handlerList:
            handlerList.append(handler)
        # print(self.__handlers)

    # ----------------------------------------------------------------------
    def removeEventListener(self, type_, handler):
        """移除监听器的处理函数"""
        try:
            handlerList = self.__handlers[type_]
            # 如果该函数存在于列表中，则移除
            if handler in handlerList:
                handlerList.remove(handler)
            # 如果函数列表为空，则从引擎中移除该事件类型
            if not handlerList:
                del self.__handlers[type_]
        except KeyError:
            pass

    # ----------------------------------------------------------------------
    def sendEvent(self, event):
        """发送事件，向事件队列中存入事件"""
        self.__eventQueue.put(event)


########################################################################
"""事件对象"""
class Event:
    # 事件类型
    RECEIVE_ADU_DATA = 'Receive_ADU_Data'
    SEND_ADU_DATA = 'Send_ADU_Data'

    RECEIVE_OLED_DATA = 'Receive_Oled_Data'
    SEND_OLED_DATA = 'Send_Oled_Data'

    RECEIVE_IOT_DATA = 'Receive_IoT_Data'
    SEND_IOT_DATA = 'Send_IoT_Data'

    RECEIVE_DTU_DATA = 'Receive_DTU_Data'
    SEND_DTU_DATA = 'Send_DTU_Data'

    RECEIVE_NM_DATA = 'Receive_NM_Data'
    SEND_NM_DATA = 'Send_NM_Data'

    # 消息字典-消息类型
    ADU_DATA = 'ADU_Data'

    OLED_DATA = 'Oled_Data'

    IOT_DATA = 'IoT_Data'

    DTU_DATA = 'DTU_Data'

    NM_DATA = 'NM_Data'

    #----------------------------------------------------------

    # Event结构：
    #       type_事件类型
    #       dict{消息类型：数据}
    def __init__(self, type_=None):
        self.type_ = type_  # 事件类型
        self.dict = {}  # 字典用于保存具体的事件数据 消息类型：数据

    # 只能有一个初始化函数，沿用老函数
    # def __init__(self, event_type=None, msg_type=None, msg_data=None):
    #     self.type_ = event_type     #事件类型
    #     self.dict = {msg_type: msg_data}    #消息字典。只能有一个消息，同消息类型多个消息会替换前面的消息数据
