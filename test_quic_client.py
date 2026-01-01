#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QUIC客户端测试脚本
模拟SN为"sn111111"的客户端与NM_Service_QUIC服务器通信
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any

# 第三方库
from aioquic.asyncio.client import connect
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived, ConnectionTerminated
from aioquic.asyncio.protocol import QuicConnectionProtocol

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 测试配置
TEST_SERVER_HOST = "192.168.3.28"
TEST_SERVER_PORT = 39999
TEST_SN = "sn111111"

class QUICTestClient:
    """QUIC测试客户端"""
    
    def __init__(self, server_host=TEST_SERVER_HOST, server_port=TEST_SERVER_PORT, sn=TEST_SN):
        self.server_host = server_host
        self.server_port = server_port
        self.sn = sn
        self.client_id = None
        self.connection = None
        self.transport = None
        self.running = False
        
        # QUIC配置
        self.configuration = QuicConfiguration(
            is_client=True,
            alpn_protocols=["comdi-nm-protocol"],
            idle_timeout=200.0,  # 调整为200秒，与服务器保持一致
        )
        
        # 开发环境禁用证书验证
        self.configuration.verify_mode = False
        
    async def start(self):
        """启动客户端并连接到服务器"""
        try:
            logger.info(f"正在连接到QUIC服务器 {self.server_host}:{self.server_port}...")
            
            self.running = True
            
            # 使用工厂函数创建协议
            def create_client_protocol(quic_protocol, *args, **kwargs):
                return TestClientProtocol(client=self, quic=quic_protocol)
            
            # 使用新版本的异步上下文管理器连接
            async with connect(
                host=self.server_host,
                port=self.server_port,
                configuration=self.configuration,
                create_protocol=create_client_protocol,
            ) as client_connection:
                self.connection = client_connection
                
                logger.info(f"✅ 成功连接到QUIC服务器！")
                
                # 发送上报数据建立SN映射
                await self.send_report_data()
                
                # 启动心跳任务
                heartbeat_task = asyncio.create_task(self.keep_alive())
                
                # 保持连接活跃
                try:
                    await self.connection.wait_closed()
                except Exception:
                    pass
                finally:
                    heartbeat_task.cancel()
                    
                return True
            
        except Exception as e:
            logger.error(f"❌ 连接QUIC服务器失败: {e}")
            return False
        finally:
            self.running = False
    
    def create_client_protocol(self, *args, **kwargs):
        """创建客户端协议实例"""
        # 移除可能冲突的参数，避免重复传递client
        filtered_kwargs = {k: v for k, v in kwargs.items() if k != 'client'}
        return TestClientProtocol(client=self, *args, **filtered_kwargs)
    
    async def send_report_data(self):
        """发送上报数据以建立SN映射"""
        try:
            # 构建上报消息
            report_data = {
                # "type": "terminal_report",
                "sn": self.sn,
                # "date": "20241201",
                # "time": "120000",
                # "op": "report",
                # "op_sub": "location_report",
                # "system_state": "normal",
                # "wireless_network_state": "connected",
                # "long": 116.397428,
                # "lat": 39.90923,
                # "theory_yaw": 0.0,
                # "yaw": 0.0,
                # "pitch": 0.0,
                # "roll": 0.0,
                # "yao_limit_state": "normal",
                # "temp": 25.0,
                # "humi": 60.0,
                # "bts_name": "Test BTS",
                # "bts_long": 116.397428,
                # "bts_lat": 39.90923,
                # "bts_no": "12345",
                # "bts_group_no": "1",
                # "bts_r": 500,
                # "upstream_rate": 1000,
                # "downstream_rate": 2000,
                # "standard": "LTE",
                # "plmn": "46000",
                # "cellid": "12345678",
                # "pci": 100,
                # "rsrp": -80,
                # "sinr": 20,
                # "rssi": -60
            }
            
            logger.info(f"📤 发送上报数据建立SN映射: {self.sn}")
            # 直接发送JSON数据，不关闭流以允许后续心跳
            data = json.dumps(report_data).encode('utf-8')
            self.connection._quic.send_stream_data(0, data, end_stream=False)
            self.connection.transmit()
            
        except Exception as e:
            logger.error(f"❌ 发送上报数据失败: {e}")
    
    async def send_heartbeat(self):
        """发送心跳包"""
        try:
            # 检查连接状态和running状态
            if not self.running or not self.connection:
                logger.info("💓 连接已断开，跳过心跳发送")
                return
            
            # 尝试检测连接是否仍然有效
            try:
                # 尝试获取连接状态，如果失败说明连接已断开
                if hasattr(self.connection, '_quic') and self.connection._quic._state:
                    state = self.connection._quic._state
                    # 检查是否处于有效状态
                    if hasattr(state, 'name') and 'closed' in state.name.lower():
                        logger.info("💓 检测到连接已关闭，跳过心跳发送")
                        self.running = False
                        return
            except Exception:
                logger.info("💓 无法检测连接状态，跳过心跳发送")
                return
                
            heartbeat_data = {
                "sn": self.sn,
                "type": "heartbeat"
            }
            
            logger.info(f"💓 发送心跳包")
            data = json.dumps(heartbeat_data).encode('utf-8')
            self.connection._quic.send_stream_data(0, data, end_stream=False)
            self.connection.transmit()
            
        except Exception as e:
            logger.error(f"❌ 发送心跳包失败: {e}")
            # 如果发送失败，可能连接已断开，设置running为False
            self.running = False
    
    async def keep_alive(self):
        """保持连接活跃，定期发送心跳"""
        while self.running:
            try:
                await asyncio.sleep(20)  # 改为每20秒发送一次心跳，更频繁地保持连接
                # 再次检查连接状态
                if self.running and self.connection:
                    await self.send_heartbeat()
                else:
                    logger.info("💓 连接已断开，停止心跳发送")
                    break
            except Exception as e:
                logger.error(f"心跳发送失败: {e}")
                self.running = False
                break


class TestClientProtocol(QuicConnectionProtocol):
    """测试客户端协议处理类"""
    
    def __init__(self, client: QUICTestClient, quic=None, *args, **kwargs):
        self.client = client
        self.pending_requests = {}  # 跟踪客户端的请求
        super().__init__(quic=quic, *args, **kwargs)
        
    def quic_event_received(self, event):
        """处理QUIC事件"""
        if isinstance(event, StreamDataReceived):
            try:
                msg_str = event.data.decode('utf-8')
                msg = json.loads(msg_str)
                logger.info(f"📥 收到服务器消息: {msg}")
                
                # 检查是否为控制指令（包含request_id）
                request_id = msg.get('request_id')
                op = msg.get('op')
                op_sub = msg.get('op_sub')
                if request_id:
                    if op == 'query' and op_sub == 'equipment_status':
                        # 回复状态查询指令
                        reply_msg = {
                            "sn": self.client.sn,
                            "op":"query_ans",
                            "op_sub":"equipment_status",
                            "request_id":request_id,
                            "IMU_stat":0,
                            "DGPS_stat":0,
                            "storage_stat":0,
                            "yaw_moto_stat":0,
                            "pitch_moto_stat":0,
                            "yaw_lim_stat":0,
                            "pitch_lim_stat":0
                        }
                        self.send_reply(reply_msg)
                        logger.info(f"📤 回复状态查询指令: {reply_msg}")
                    else:
                        # 其他查询指令，默认回复成功
                        reply_msg = {
                            "sn": self.client.sn,
                            "op":"ans",
                            "op_sub":op_sub,
                            "status": "success",
                            "message": f"成功收到查询指令：{json.dumps(msg, ensure_ascii=False)}"
                        }
                        self.send_reply(reply_msg)
                else:
                    # 普通消息，直接回复确认
                    reply_msg = {
                        "type": "response",
                        "sn": self.client.sn,
                        "status": "success",
                        "message": f"成功收到消息：{json.dumps(msg, ensure_ascii=False)}"
                    }
                    
                    logger.info(f"📤 回复普通消息: {reply_msg}")
                    self.send_reply(reply_msg)
                
            except json.JSONDecodeError:
                logger.error(f"收到非JSON数据: {event.data}")
            except Exception as e:
                logger.error(f"处理消息异常: {e}")
                
        elif isinstance(event, ConnectionTerminated):
            logger.info(f"🔌 服务器断开连接: {event.reason_phrase}")
            self.client.running = False
    
    def send_reply(self, msg_dict):
        """发送回复消息"""
        try:
            data = json.dumps(msg_dict).encode('utf-8')
            self._quic.send_stream_data(0, data, end_stream=True)
            self.transmit()
            logger.info(f"📤 已发送回复到服务器")
        except Exception as e:
            logger.error(f"❌ 发送回复失败: {e}")


async def main():
    """主函数"""
    client = QUICTestClient(TEST_SERVER_HOST, TEST_SERVER_PORT, TEST_SN)
    
    try:
        # 启动客户端
        success = await client.start()
        
        if success:
            logger.info("🎉 客户端连接建立成功！")
            logger.info(f"📱 SN: {client.sn} 已建立连接")
            logger.info("💡 客户端将保持在线并响应服务器消息")
        else:
            logger.error("❌ 无法连接到服务器")
            
    except KeyboardInterrupt:
        logger.info("🛑 用户中断连接")
    except Exception as e:
        logger.error(f"❌ 客户端异常: {e}")


if __name__ == "__main__":
    print("🚀 启动QUIC测试客户端")
    print(f"📱 SN: {TEST_SN}")
    print(f"🌐 服务器: {TEST_SERVER_HOST}:{TEST_SERVER_PORT}")
    print("=" * 50)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 客户端已退出")