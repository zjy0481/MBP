# -*- coding:utf-8 -*-

import logging
import os
import time
from logging.handlers import RotatingFileHandler
from queue import Queue

import colorlog

log_colors_config = {
    'DEBUG': 'cyan',  # black, red, green, yellow, blue, purple, cyan, white
    'INFO': 'green',
    'WARNING': 'purple',
    'ERROR': 'red',
    'CRITICAL': 'bold_red',
}


class ExtendHandler(logging.Handler, object):
    """
    自定义日志handler
    """

    def __init__(self, name, other_attr=None, **kwargs):
        logging.Handler.__init__(self)
        # print('初始化日志处理器：', name)

    def emit(self, record: logging.LogRecord) -> None:
        """
        emit函数为自定义handler必须重写的函数，这里根据需要增加一些处理
        :param record:
        :return:
        """
        try:
            message = self.format(record)
        except Exception:
            self.handleError(record)

        if record.levelname == 'DEBUG':
            LoggerManage.send_to_web(
                dict(
                    cmd=0xF1,  # 日志消息命令字
                    level=0,  # 调试信息
                    time=time.strftime('%Y-%m-%d %H:%M:%S'),
                    msg=message
                )
            )
        elif record.levelname == 'INFO':
            LoggerManage.send_to_web(
                dict(
                    cmd=0xF1,  # 日志消息命令字
                    level=1,  # 提示信息
                    time=time.strftime('%Y-%m-%d %H:%M:%S'),
                    msg=message
                )
            )
        elif record.levelname == 'WARNING':
            LoggerManage.send_to_web(
                dict(
                    cmd=0xF1,  # 日志消息命令字
                    level=2,  # 警告信息
                    time=time.strftime('%Y-%m-%d %H:%M:%S'),
                    msg=message
                )
            )
        elif record.levelname == 'ERROR':
            LoggerManage.send_to_web(
                dict(
                    cmd=0xF1,  # 日志消息命令字
                    level=3,  # 错误信息
                    time=time.strftime('%Y-%m-%d %H:%M:%S'),
                    msg=message
                )
            )
        elif record.levelname == 'CRITICAL':
            LoggerManage.send_to_web(
                dict(
                    cmd=0xF1,  # 日志消息命令字
                    level=4,  # 严重错误
                    time=time.strftime('%Y-%m-%d %H:%M:%S'),
                    msg=message
                )
            )
        else:
            pass


class LoggerManage(object):
    """
    日志处理类
    """
    # 类属性
    # web消息队列
    __to_web_messages = None

    def __init__(self, app_name="youApp", log_path='', log_level=logging.DEBUG, log_file_size=10, log_file_backup=5,
                 log_formatter_str=''):
        """
        :param app_name: 应用程序名称，作为创建日志的根节点名称
        初始化日志模块，创建相应的logger，handler，filter，formatter
        """
        # 初始化属性
        # 如果日志路径为空或者给出的路径非目录，设置当前路径+/Logs/为日志目录
        if log_path == '' or not os.path.isdir(log_path):
            cur_path = os.path.abspath(os.path.dirname(__file__))
            self.__log_path = cur_path + "/Logs/"
        self.__log_level = log_level
        self.__log_file_size = log_file_size * 1024 * 1024  # 转换成 M bytes
        self.__log_file_backup = log_file_backup
        if log_formatter_str == '':
            self.__log_formatter_str = '[%(asctime)s] %(filename)s -> [line: %(lineno)d](func: %(funcName)s)' \
                                       '<thd: %(threadName)s> - %(levelname)s:\n%(message)s'

        # 第一步，创建一个logger
        # 可以通过logging.getLogger(name)获取logger对象，
        # 如果不指定name则返回root对象，多次使用相同的name调用getLogger方法返回同一个logger对象。
        self.logger = logging.getLogger()
        self.logger.handlers.clear()  # 清除logger,避免多个文件引用重复打印log
        self.logger.setLevel(self.__log_level)  # Log等级总开关。指定日志的最低输出级别，默认为WARN级别

        # 第二步，创建一个文件handler，用于写入日志文件
        # 一个logger对象可以通过addHandler方法添加0到多个handler，
        # 每个handler又可以定义不同日志级别，以实现日志分级过滤显示。
        # 创建日志目录
        if os.path.exists(self.__log_path) and os.path.isdir(self.__log_path):
            pass
        else:
            os.mkdir(self.__log_path)  # 创建目录
        # print(log_path)
        log_name = self.__log_path + app_name + '.log'  # 指定输出的日志文件名

        # 定义一个RotatingFileHandler，最多备份3个日志文件，每个日志文件最大10K
        fh = RotatingFileHandler(log_name, mode='a', maxBytes=self.__log_file_size, backupCount=self.__log_file_backup,
                                 encoding='utf-8')
        fh.setLevel(self.__log_level)

        # 再创建一个控制台流handler，用于输出到控制台
        ch = logging.StreamHandler()
        ch.setLevel(self.__log_level)

        # 创建一个自定义扩展handler，用于自定义处理
        eh = ExtendHandler('Extend_log_handler')
        eh.setLevel(self.__log_level)

        # 第三步，定义handler的输出格式
        formatter = logging.Formatter(self.__log_formatter_str)
        console_formatter = colorlog.ColoredFormatter(
            fmt='%(log_color)s' + self.__log_formatter_str,
            log_colors=log_colors_config
        )
        # 设置每个handler的输出格式
        fh.setFormatter(formatter)
        ch.setFormatter(console_formatter)
        eh.setFormatter(formatter)

        # 第四步，将logger添加到handler里面
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        self.logger.addHandler(eh)

    def get_logger(self):
        return self.logger

    # def web_debug(self, message):
    #     """
    #     :param message: debug信息
    #     :return:
    #     """
    #     # self.logger.debug(message)
    #     self.send_to_web(
    #         dict(
    #             cmd=0xF1,  # 日志消息命令字
    #             level=0,  # 调试信息
    #             time=time.strftime('%Y-%m-%d %H:%M:%S'),
    #             msg=message
    #         )
    #     )
    #
    # def web_info(self, message):
    #     """
    #     :param message: info信息
    #     :return:
    #     """
    #     # self.logger.info(message)
    #     self.send_to_web(
    #         dict(
    #             cmd=0xF1,  # 日志消息命令字
    #             level=1,  # 提示信息
    #             time=time.strftime('%Y-%m-%d %H:%M:%S'),
    #             msg=message
    #         )
    #     )
    #
    # def web_warning(self, message):
    #     """
    #     :param warn: warn 信息
    #     :return:
    #     """
    #     # self.logger.warning(message)
    #     self.send_to_web(
    #         dict(
    #             cmd=0xF1,  # 日志消息命令字
    #             level=2,  # 警告信息
    #             time=time.strftime('%Y-%m-%d %H:%M:%S'),
    #             msg=message
    #         )
    #     )
    #
    # def web_error(self, message):
    #     """
    #     :param message: error 信息
    #     :return:
    #     """
    #     # self.logger.error(message)
    #     self.send_to_web(
    #         dict(
    #             cmd=0xF1,  # 日志消息命令字
    #             level=3,  # 错误信息
    #             time=time.strftime('%Y-%m-%d %H:%M:%S'),
    #             msg=message
    #         )
    #     )
    #
    # def web_critical(self, message):
    #     """
    #     :param message: critical 信息
    #     :return:
    #     """
    #     # self.logger.critical(message)
    #     self.send_to_web(
    #         dict(
    #             cmd=0xF1,  # 日志消息命令字
    #             level=4,  # 严重错误
    #             time=time.strftime('%Y-%m-%d %H:%M:%S'),
    #             msg=message
    #         )
    #     )

    # 绑定发给web的消息队列
    @classmethod
    def bind_web_message_queue(cls, queue: Queue):
        if isinstance(queue, Queue):
            cls.__to_web_messages = queue
        else:
            print("Web消息队列绑定失败")

    # 发送日志信息给Web
    @classmethod
    def send_to_web(cls, msg):
        if cls.__to_web_messages is not None:
            cls.__to_web_messages.put(msg)
        else:
            print("请先绑定Web消息队列。Web消息发送失败：" + str(msg))  # 这里直接打印（不发给Web），否则会递归调用


if __name__ == '__main__':
    logger = LoggerManage(app_name='logTest').get_logger()
    LoggerManage.bind_web_message_queue(Queue())

    logger.debug('这是 logger debug message')
    logger.info('这是 logger info message')
    logger.warning('这是 logger warning message')
    logger.error('这是 logger error message')
    logger.critical('这是 logger critical message')

    time.sleep(10)

    print(LoggerManage.__to_web_messages.get())
