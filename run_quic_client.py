#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QUIC客户端快速启动脚本
"""

import sys
import os
import asyncio
from test_quic_client import main

if __name__ == "__main__":
    print("🚀 QUIC客户端测试工具")
    print("=" * 40)
    print("📋 功能说明:")
    print("1. 连接到QUIC服务器 (127.0.0.1:59999)")
    print("2. 模拟SN为'sn111111'的客户端")
    print("3. 建立SN到client_id的映射")
    print("4. 接收服务器消息并自动回复")
    print("5. 定期发送心跳保持连接")
    print("=" * 40)
    
    try:
        print("🔄 正在启动客户端...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 客户端已退出")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)