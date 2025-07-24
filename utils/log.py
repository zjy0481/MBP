# utils/log.py
# -*- coding:utf-8 -*-

import logging
import os
import time
from logging.handlers import RotatingFileHandler

import colorlog
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

log_colors_config = {
    'DEBUG': 'cyan',
    'INFO': 'green',
    'WARNING': 'purple',
    'ERROR': 'red',
    'CRITICAL': 'bold_red',
}

class ExtendHandler(logging.Handler):
    """
    自定义日志handler，用于将日志记录发送到Web前端。
    """
    def __init__(self, **kwargs):
        logging.Handler.__init__(self)

    def emit(self, record: logging.LogRecord) -> None:
        """
        当日志被记录时，此方法被调用。
        它将日志记录格式化成字典，并调用LoggerManage的发送方法。
        """
        try:
            # 沿用您原有的逻辑，将日志级别转换为数字
            level_map = {
                'DEBUG': 0, 'INFO': 1, 'WARNING': 2, 'ERROR': 3, 'CRITICAL': 4
            }
            log_entry = {
                'cmd': 0xF1,  # 日志消息命令字
                'level': level_map.get(record.levelname, 1),
                'time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'msg': self.format(record)
            }
            LoggerManage.send_to_web(log_entry)
        except Exception:
            self.handleError(record)


class LoggerManage:
    """
    日志处理类。
    """
    # web消息队列已被移除

    def __init__(self, app_name="MBP", log_path='', log_level=logging.DEBUG, **kwargs):
        """
        初始化日志模块。
        """
        if not log_path or not os.path.isdir(log_path):
            cur_path = os.path.dirname(os.path.abspath(__file__))
            self.__log_path = os.path.join(cur_path, "Logs")
        
        self.__log_formatter_str = '[%(asctime)s] %(filename)s -> [line: %(lineno)d] - %(levelname)s: %(message)s'

        self.logger = logging.getLogger()
        if self.logger.hasHandlers():
            self.logger.handlers.clear()
        self.logger.setLevel(log_level)

        # 确保日志目录存在
        os.makedirs(self.__log_path, exist_ok=True)
        log_name = os.path.join(self.__log_path, f'{app_name}.log')

        # 文件处理器
        fh = RotatingFileHandler(log_name, mode='a', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
        fh.setLevel(log_level)
        
        # 控制台处理器
        ch = colorlog.StreamHandler()
        ch.setLevel(log_level)
        
        # 我们自定义的Web推送处理器
        eh = ExtendHandler()
        eh.setLevel(log_level)

        # 定义格式化器
        formatter = logging.Formatter(self.__log_formatter_str)
        console_formatter = colorlog.ColoredFormatter(
            fmt='%(log_color)s' + self.__log_formatter_str,
            log_colors=log_colors_config
        )

        fh.setFormatter(formatter)
        ch.setFormatter(console_formatter)
        # 为Web推送处理器使用一个更简洁的格式
        eh.setFormatter(logging.Formatter('%(message)s'))

        # 添加处理器
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        self.logger.addHandler(eh)

    def get_logger(self):
        return self.logger

    @staticmethod
    def send_to_web(msg: dict):
        """
        [核心修改]
        使用Django Channels Layer将日志消息广播给所有连接的WebSocket客户端。
        """
        try:
            channel_layer = get_channel_layer()
            if channel_layer is not None:
                # 使用 async_to_sync 包装异步方法，以便在同步代码中调用
                async_to_sync(channel_layer.group_send)(
                    "terminal_updates",  # 目标组名，必须与Consumer中的一致
                    {
                        "type": "log.message",  # 自定义事件类型
                        "message": msg
                    }
                )
        except Exception as e:
            # 如果在日志系统中发生错误，只能打印到控制台，避免无限循环
            print(f"CRITICAL: Failed to send log to web via Channels: {e}")