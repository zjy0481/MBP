from django.apps import AppConfig


class TerminalManagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "terminal_management"

    # 添加 ready 方法
    def ready(self):
        # 导入 signals.py 来注册信号处理器
        import terminal_management.signals