# utils/__init__.py
#  _*_ coding: utf_8  _*_

from .log import LoggerManage

# 初始化日志管理器，这将配置好文件、控制台和Web推送处理器
# app_name会作为日志文件名的一部分
gl_logman = LoggerManage(app_name='MBP_System')

# 创建一个全局可用的logger实例
gl_logger = gl_logman.get_logger()