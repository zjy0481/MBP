from django.apps import AppConfig


class TerminalManagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "terminal_management"

    def ready(self):
        # 导入并注册signals
        import terminal_management.signals
