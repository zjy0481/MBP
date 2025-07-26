# terminal_management/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer

class DataConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'data_updates'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # 自定义方法，用于从 channel layer 接收消息并推送给前端
    async def send_update(self, event):
        message = event['message']
        await self.send(text_data=json.dumps(message))