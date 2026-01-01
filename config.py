#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件读取脚本
用于读取和管理config.toml中的配置信息
"""

import os
import sys
import toml
from typing import Any, Dict, Optional, Union
from pathlib import Path


class Config:
    """配置管理类"""
    
    def __init__(self, config_path: str = "config.toml"):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认为config.toml
        """
        self.config_path = config_path
        self._config_data = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """加载配置文件"""
        try:
            config_file_path = Path(self.config_path)
            if not config_file_path.exists():
                raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
            
            with open(config_file_path, 'r', encoding='utf-8') as f:
                self._config_data = toml.load(f)
            
            print(f"✅ 成功加载配置文件: {self.config_path}")
            
        except FileNotFoundError as e:
            print(f"❌ 配置文件错误: {e}")
            sys.exit(1)
        except toml.TomlDecodeError as e:
            print(f"❌ TOML格式错误: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ 加载配置文件时发生错误: {e}")
            sys.exit(1)
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值，支持点号分隔的路径
        
        Args:
            key_path: 配置键路径，如 'web_config.web_host' 或 'database.password'
            default: 默认值
            
        Returns:
            配置值或默认值
        """
        keys = key_path.split('.')
        value = self._config_data
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def validate_config(self) -> bool:
        """验证配置文件完整性和有效性"""
        required_sections = ['web_config']
        required_keys = {
            'web_config': [
                'web_host', 'web_port', 'web_secret_key',
                'database_host', 'database_port', 'database_name',
                'redis_host', 'redis_port',
                'quic_host', 'quic_port'
            ]
        }
        
        try:
            # 检查必需的配置节
            for section in required_sections:
                if section not in self._config_data:
                    print(f"❌ 缺少必需的配置节: {section}")
                    return False
            
            # 检查必需的键
            for section, keys in required_keys.items():
                for key in keys:
                    if key not in self._config_data.get(section, {}):
                        print(f"❌ 缺少必需的配置文件键: {section}.{key}")
                        return False
            
            print("✅ 配置文件验证通过")
            return True
            
        except Exception as e:
            print(f"❌ 配置验证失败: {e}")
            return False


# 全局配置实例
_config_instance = None

def get_config(config_path: str = "config.toml") -> Config:
    """
    获取全局配置实例（单例模式）
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置实例
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance


# if __name__ == "__main__":
#     # 命令行使用示例
#     if len(sys.argv) > 1:
#         config_path = sys.argv[1]
#     else:
#         config_path = "config.toml"
    
#     # 加载配置
#     config = get_config(config_path)
    
#     # 验证配置
#     config.validate_config()
    
#     # 打印配置摘要
#     config.print_config_summary()
    
#     # 演示获取特定配置
#     print("\n🔍 配置获取示例:")
#     print(f"Web Host: {config.get('web_config.web_host')}")
#     print(f"Redis Port: {config.get('web_config.redis_port')}")
#     print(f"QUIC Port: {config.get('web_config.quic_port')}")
#     print(f"Log Level: {config.get('web_config.log_level')}")