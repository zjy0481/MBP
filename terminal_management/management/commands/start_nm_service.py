from django.core.management.base import BaseCommand
from acu.NM_Service import NM_Service
import time

class Command(BaseCommand):
    help = '启动UDP NM_Service来监听端站上报'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('正在启动 NM_Service...'))

        service = NM_Service()
        service.start()

        self.stdout.write(self.style.SUCCESS('NM_Service 正在运行。按 CTRL+C 停止。'))

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n正在停止 NM_Service...'))
            service.stop()
            self.stdout.write(self.style.SUCCESS('NM_Service 已成功停止。'))