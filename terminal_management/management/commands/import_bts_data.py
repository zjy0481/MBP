import json
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from terminal_management.models import BaseStationInfo

class Command(BaseCommand):
    """
    一个Django管理命令，用于从指定的JSON文件导入基站信息到数据库。
    
    用法:
        python manage.py import_bts_data /path/to/your/data.json
    """
    help = '从指定的JSON文件导入基站数据到 BaseStationInfo 表'

    def add_arguments(self, parser):
        """
        为命令添加一个必需的位置参数，即JSON文件的路径。
        """
        parser.add_argument('json_file_path', type=str, help='包含基站数据的JSON文件的路径')

    def handle(self, *args, **options):
        """
        命令的主要执行逻辑。
        """
        json_file_path = options['json_file_path']
        
        # 打印开始信息
        self.stdout.write(self.style.SUCCESS(f'--- 开始从 {json_file_path} 导入基站数据 ---'))

        # 检查文件是否存在
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f'错误: 文件 "{json_file_path}" 未找到。')
        except json.JSONDecodeError:
            raise CommandError(f'错误: 文件 "{json_file_path}" 不是一个有效的JSON文件。')
        
        # 确保JSON数据是列表格式
        if not isinstance(data, list):
            raise CommandError('错误: JSON文件的顶层结构必须是一个列表 (JSON array)。')

        # 记录创建和更新的数量
        created_count = 0
        updated_count = 0

        try:
            # 使用数据库事务，确保数据导入的原子性
            # 如果中途出现任何错误，所有已做的更改都会被回滚
            with transaction.atomic():
                for item in data:
                    # 从JSON项中获取主键 bts_id
                    bts_id = item.get('bts_id')
                    if bts_id is None:
                        self.stdout.write(self.style.WARNING(f'跳过一条记录，因为它缺少 "bts_id": {item}'))
                        continue

                    # 使用 update_or_create 方法
                    # 这个方法会尝试用 bts_id 来获取一个对象：
                    # - 如果找到了，它就会用 item 中的其他数据来更新这个对象。
                    # - 如果没找到，它就会用 item 中的所有数据创建一个新对象。
                    # 这可以完美地防止重复创建，并且允许用新的JSON文件来更新已有数据。
                    obj, created = BaseStationInfo.objects.update_or_create(
                        bts_id=str(bts_id),  # 确保 bts_id 是字符串，与模型定义一致
                        defaults=item
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(f'  [创建] 基站: {obj.bts_name} (ID: {obj.bts_id})')
                    else:
                        updated_count += 1
                        self.stdout.write(f'  [更新] 基站: {obj.bts_name} (ID: {obj.bts_id})')

        except Exception as e:
            raise CommandError(f'导入过程中发生严重错误: {e}')

        # 打印结束信息
        self.stdout.write(self.style.SUCCESS('--- 导入完成 ---'))
        self.stdout.write(self.style.SUCCESS(f'总计: 成功创建 {created_count} 条新记录，更新 {updated_count} 条现有记录。'))