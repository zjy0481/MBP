#  _*_ coding: utf_8  _*_

import utils.log as log
from config import get_config
config = get_config()
DEFAULT_LOG_LEVEL = config.get("logger_config.log_level", "INFO")

# 公共日志模块
gl_logman = log.LoggerManage(app_name='ACS', log_level=DEFAULT_LOG_LEVEL)
gl_logger = gl_logman.get_logger()
