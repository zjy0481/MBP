# terminal_management/management/commands/start_nm_service_quic.py

from django.core.management.base import BaseCommand
import asyncio
import signal
import sys

class Command(BaseCommand):
    help = '启动QUIC版本的NM_Service来监听端站上报'

    def handle(self, *args, **options):
        # 设置信号处理
        def signal_handler(sig, frame):
            self.stdout.write(self.style.WARNING('\n正在停止 NM_Service...'))
            asyncio.create_task(self._cleanup_service())
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # 运行异步主循环
        try:
            self.stdout.write(self.style.SUCCESS('正在启动 QUIC版本的 NM_Service...'))
            asyncio.run(self._run_service())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n正在停止 NM_Service...'))
            asyncio.run(self._cleanup_service())
            self.stdout.write(self.style.SUCCESS('NM_Service 已成功停止。'))

    async def _run_service(self):
        """异步运行服务"""
        try:
            # 在异步上下文中导入
            from acu.NM_Service_quic import get_nm_service_quic
            
            # 获取全局服务实例
            service = await get_nm_service_quic()
            
            # 启动服务
            await service.start()
            
            self.stdout.write(self.style.SUCCESS('QUIC NM_Service 正在运行。按 CTRL+C 停止。'))
            
            # 保持服务运行
            while service.is_running:
                await asyncio.sleep(1)
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'服务运行出错: {str(e)}'))
            await self._cleanup_service()
            raise
        finally:
            self.stdout.write(self.style.WARNING('服务已停止运行'))

    async def _cleanup_service(self):
        """清理服务资源"""
        try:
            # 在异步上下文中导入
            from acu.NM_Service_quic import stop_nm_service_quic
            await stop_nm_service_quic()
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'服务停止时出现警告: {str(e)}'))