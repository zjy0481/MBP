# terminal_management/consumers.py
import json
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from . import services
from acu.Protocol import CommandWord # 导入您旧项目中的CommandWord

class MainConsumer(WebsocketConsumer):
    # 当WebSocket连接建立时调用
    def connect(self):
        self.group_name = "terminal_updates"  # 为所有客户端定义一个组名
        
        # 将当前连接加入到组中，以便接收广播
        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name
        )
        
        self.accept()
        print(f"WebSocket连接已建立: {self.channel_name}")

    # 当WebSocket连接断开时调用
    def disconnect(self, close_code):
        print(f"WebSocket连接已断开: {close_code}")
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name,
            self.channel_name
        )

    # 当从客户端收到消息时调用
    def receive(self, text_data):
        """
        处理从前端JS发送过来的指令。
        这部分逻辑完全迁移自Tornado的on_message方法。
        """
        try:
            data = json.loads(text_data)
            cmd = data.get('cmd')
            print(f"收到来自客户端的指令: {data}")
            
            # TODO: 未来在这里调用services层函数，通过UDP将指令发送出去
            # 例如: services.send_udp_command(data)
            # 目前只打印日志
            if cmd == CommandWord.SET_BTS_INFO.value:
                print("模拟: 设置基站信息")
            elif cmd == CommandWord.GET_DEVICE_STATUS.value:
                print("模拟: 查询设备状态")
                # 我们可以模拟一个回复给发送者
                self.send(text_data=json.dumps({
                    'cmd': CommandWord.GET_DEVICE_STATUS.value,
                    'IMUState': 0, 'DGPSState': 0, 'storageState': 0,
                    'yawMotoState': 0, 'pitchMotoState': 0, 'yawLimitState': 0,
                    'pitchLimitState': 0
                }))
            # todo:... 在此补完所有其他的elif指令分支 ...
            else:
                print(f"收到未知指令: {cmd}")

        except Exception as e:
            print(f"处理客户端消息时出错: {e}")

    # --- 用于从后端其他地方接收广播消息并发送给前端 ---
    def terminal_report_message(self, event):
        """
        这是一个自定义的事件处理器。
        当Django Signals广播消息时，Channels会自动调用这个同名方法。
        `event`中包含了从signal传递过来的数据。
        """
        message = event['message']
        
        # 将收到的Python字典打包成JSON字符串，发送给前端
        self.send(text_data=json.dumps(message))
        print(f"已向客户端 {self.channel_name} 推送实时数据")

    def log_message(self, event):
        """
        处理由日志系统广播过来的消息。
        方法名 'log_message' 对应于事件类型 'log.message'。
        """
        message = event['message']
        # 直接将已经格式化好的JSON字典发送给前端
        self.send(text_data=json.dumps(message))