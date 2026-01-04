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

# 日志等级映射
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
    'FATAL': logging.CRITICAL  # 将FATAL映射到CRITICAL
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
        """
        # 在发送前检查队列是否存在
        if LoggerManage.is_web_queue_bound():
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

    def __init__(self, app_name="youApp", log_path='', log_level="INFO", log_file_size=10, log_file_backup=5,
                 log_formatter_str=''):
        """
        :param app_name: 应用程序名称，作为创建日志的根节点名称
        :param log_level: 日志等级，支持 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'FATAL'
        初始化日志模块，创建相应的logger，handler，filter，formatter
        """
        # 初始化属性
        # 如果日志路径为空或者给出的路径非目录，设置当前路径+/Logs/为日志目录
        if log_path == '' or not os.path.isdir(log_path):
            cur_path = os.path.abspath(os.path.dirname(__file__))
            self.__log_path = cur_path + "/Logs/"
        
        # 转换日志等级字符串为logging常量
        self.__log_level = self._get_log_level(log_level)
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
        self.logger.setLevel(self.__log_level)  # Log等级总开关。指定日志的最低输出级别

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

    def _get_log_level(self, level_str):
        """
        将日志等级字符串转换为logging常量
        """
        level_str = level_str.upper()
        if level_str in LOG_LEVELS:
            return LOG_LEVELS[level_str]
        else:
            # 默认使用INFO级别
            print(f"未知的日志等级 '{level_str}'，使用默认的INFO级别")
            return logging.INFO

    def set_log_level(self, level_str):
        """
        动态设置日志等级
        :param level_str: 日志等级字符串，支持 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'FATAL'
        """
        new_level = self._get_log_level(level_str)
        self.__log_level = new_level
        self.logger.setLevel(new_level)
        
        # 同时更新所有handler的等级
        for handler in self.logger.handlers:
            handler.setLevel(new_level)
        
        print(f"日志等级已设置为: {level_str}")

    def get_log_level(self):
        """
        获取当前日志等级
        :return: 当前日志等级字符串
        """
        level_map = {v: k for k, v in LOG_LEVELS.items()}
        return level_map.get(self.__log_level, 'UNKNOWN')

    def get_logger(self):
        return self.logger

    @classmethod
    def set_global_log_level(cls, level_str):
        """
        类方法：全局设置所有logger的日志等级
        :param level_str: 日志等级字符串
        """
        # 直接获取logging等级，不创建LoggerManage实例
        level = cls._get_log_level_static(level_str)
        logging.getLogger().setLevel(level)
        print(f"全局日志等级已设置为: {level_str}")
    
    @staticmethod
    def _get_log_level_static(level_str):
        """
        静态方法：将日志等级字符串转换为logging常量（不创建实例）
        """
        level_str = level_str.upper()
        if level_str in LOG_LEVELS:
            return LOG_LEVELS[level_str]
        else:
            # 默认使用INFO级别
            print(f"未知的日志等级 '{level_str}'，使用默认的INFO级别")
            return logging.INFO

    @classmethod
    def get_available_log_levels(cls):
        """
        获取可用的日志等级列表
        :return: 可用的日志等级列表
        """
        return list(LOG_LEVELS.keys())

    #检查队列绑定状态
    @classmethod
    def is_web_queue_bound(cls):
        return hasattr(cls, '_LoggerManage__to_web_messages') and cls.__to_web_messages is not None

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

# 使用示例和测试代码
if __name__ == '__main__':
    # 创建日志管理器，默认使用INFO级别（不显示debug）
    logger_manager = LoggerManage(app_name='logTest')
    logger = logger_manager.get_logger()
    LoggerManage.bind_web_message_queue(Queue())

    print("=== 当前日志等级测试 ===")
    print(f"当前日志等级: {logger_manager.get_log_level()}")
    print(f"可用日志等级: {logger_manager.get_available_log_levels()}")

    print("\n=== 不同级别日志测试 ===")
    logger.debug('这是 logger debug message - 不会显示')
    logger.info('这是 logger info message - 会显示')
    logger.warning('这是 logger warning message - 会显示')
    logger.error('这是 logger error message - 会显示')
    logger.critical('这是 logger critical message - 会显示')
    logger.fatal('这是 logger fatal message - 会显示')

    print("\n=== 动态修改日志等级为DEBUG ===")
    logger_manager.set_log_level('DEBUG')
    print(f"当前日志等级: {logger_manager.get_log_level()}")
    logger.debug('这是 logger debug message - 现在会显示')

    print("\n=== 动态修改日志等级为ERROR ===")
    logger_manager.set_log_level('ERROR')
    print(f"当前日志等级: {logger_manager.get_log_level()}")
    logger.info('这是 logger info message - 现在不会显示')
    logger.error('这是 logger error message - 现在会显示')

    print("\n=== 全局设置日志等级 ===")
    LoggerManage.set_global_log_level('WARNING')
    
    print("\n测试完成！")