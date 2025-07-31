# terminal_management/models.py

from django.db import models
# 由于该项目的网页用户管理较为简单，因此直接导入 Django 内置的用户模型，并将直接使用它
from django.contrib.auth.models import User

# -----------------------------------------------------------------------------
# 1. 船信息表 (ShipInfo)
#    - 继承自 models.Model，这是定义 Django 模型的基础。
# -----------------------------------------------------------------------------
class ShipInfo(models.Model):
    """
    存储船舶的基本信息。
    """
    mmsi = models.CharField(
        primary_key=True,  # 将 MMSI 设置为主键
        max_length=9,      # 海上移动通信业务标识码 (MMSI) 通常是9位数字
        verbose_name="MMSI号码"
    )
    ship_name = models.CharField(
        max_length=100,
        verbose_name="船名"
    )
    # 船舶呼号是唯一的，因此将它设置为 unique=True，并为其创建数据库索引 db_index=True 以提高查询效率
    call_sign = models.CharField(
        max_length=20,
        unique=True, 
        db_index=True, 
        verbose_name="呼号"
    )
    ship_owner = models.CharField(
        max_length=100,
        verbose_name="船东",
        blank=True, # 允许该字段为空
        null=True   # 允许数据库中该字段为 NULL
    )

    def __str__(self):
        # 定义模型的字符串表示形式，方便在 Admin 后台或调试时查看
        return f"{self.ship_name} ({self.mmsi})"

    class Meta:
        # 定义模型的元数据
        verbose_name = "船舶信息"        # 单数形式的名称
        verbose_name_plural = "船舶信息" # 复数形式的名称


# -----------------------------------------------------------------------------
# 2. 端站信息表 (TerminalInfo)
#    - 描述安装在船上的具体设备（端站）。
# -----------------------------------------------------------------------------
class TerminalInfo(models.Model):
    """
    存储船上端站（设备）的信息。
    """
    sn = models.CharField(
        primary_key=True,   # 设备序列号 (SN) 作为主键
        max_length=50, 
        verbose_name="SN码"
    )
    # 外键 ForeignKey，用于关联到 ShipInfo 表。
    # to='ShipInfo' 指定了关联的模型。
    # on_delete=models.CASCADE 表示级联删除：如果一艘船的信息被删除了，那么这艘船上所有的端站信息也会被一并删除。
    # to_field='call_sign' 指定了外键关联到 ShipInfo 表的 call_sign 字段，而不是默认的主键 mmsi。
    ship = models.ForeignKey(
        to='ShipInfo', 
        on_delete=models.CASCADE,
        verbose_name="所属船舶"
    )
    ip_address = models.GenericIPAddressField(
        verbose_name="IP地址",
        blank=True,
        null=True
    )
    port_number = models.PositiveIntegerField(
        verbose_name="端口号",
        blank=True,
        null=True
    )

    def __str__(self):
        return f"端站SN: {self.sn} (属于: {self.ship.ship_name})"

    class Meta:
        verbose_name = "端站信息"
        verbose_name_plural = "端站信息"


# -----------------------------------------------------------------------------
# 3. 基站信息表 (BaseStationInfo)
#    - 存储地面基站的参数。
# -----------------------------------------------------------------------------
class BaseStationInfo(models.Model):
    """
    存储地面基站的信息。
    """
    bts_id = models.CharField(
        primary_key=True, # 基站ID作为主键
        max_length=50,
        verbose_name="基站ID"
    )
    bts_name = models.CharField(
        max_length=100,
        unique=True,  # 基站名称这里也设为唯一的
        verbose_name="基站名称"
    )
    # “频段”字段已删除
    # frequency_band = models.CharField(
    #     max_length=50,
    #     verbose_name="频段",
    #     blank=True,
    #     null=True
    # )
    coverage_distance = models.FloatField(
        verbose_name="覆盖距离(公里)",
        help_text="单位：公里", 
        blank=True,
        null=True
    )
    region_code = models.CharField(
        max_length=50,
        verbose_name="地区号",
        blank=True,
        null=True
    )
    # 这里使用了FloatField来表示经纬度。如果需要极高精度，可以改用 DecimalField。
    longitude = models.FloatField(
        verbose_name="站点经度",
        blank=True,
        null=True
    )
    latitude = models.FloatField(
        verbose_name="站点纬度",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.bts_name

    class Meta:
        verbose_name = "基站信息"
        verbose_name_plural = "基站信息"


# -----------------------------------------------------------------------------
# 4. 端站上报信息表 (TerminalReport)
#    - 记录端站设备上报的各种状态和参数。
# -----------------------------------------------------------------------------
class TerminalReport(models.Model):
    """
    存储端站上报的详细信息。
    这是系统的核心数据，数据量可能会很大。
    """
    
    # -- 复合唯一约束字段 --
    type = models.IntegerField(verbose_name="设备类型号")
    sn = models.CharField(max_length=50, verbose_name="设备序列号", db_index=True) # 经常用于查询，添加索引
    report_date = models.DateField(verbose_name="上报日期", db_index=True) # 名字用 report_date 避免与 Python 关键字冲突
    report_time = models.TimeField(verbose_name="上报时间") # 名字用 report_time

    # -- 操作信息 --
    op = models.IntegerField(verbose_name="操作类型")
    op_sub = models.IntegerField(verbose_name="操作子类")

    # -- 端站状态信息 --
    long = models.FloatField(verbose_name="端站经度", blank=True, null=True)
    lat = models.FloatField(verbose_name="端站纬度", blank=True, null=True)
    theory_yaw = models.FloatField(verbose_name="理论方位角", blank=True, null=True)
    yaw = models.FloatField(verbose_name="当前方位角", blank=True, null=True)
    pitch = models.FloatField(verbose_name="当前俯仰角", blank=True, null=True)
    roll = models.FloatField(verbose_name="当前横滚角", blank=True, null=True)
    yao_limit_state = models.CharField(max_length=50, verbose_name="方位限位", blank=True, null=True)
    temp = models.FloatField(verbose_name="温度(°C)", blank=True, null=True)
    humi = models.FloatField(verbose_name="湿度(%)", blank=True, null=True)

    # -- 基站相关信息 --
    bts_name = models.CharField(max_length=100, verbose_name="基站名", blank=True, null=True)
    bts_long = models.FloatField(verbose_name="基站经度", blank=True, null=True)
    bts_lat = models.FloatField(verbose_name="基站纬度", blank=True, null=True)
    bts_freq = models.CharField(max_length=50, verbose_name="基站频段", blank=True, null=True)
    bts_r = models.FloatField(verbose_name="基站覆盖半径(公里)", blank=True, null=True)

    # -- 通信质量信息 --
    upstream_rate = models.FloatField(verbose_name="上行速率(Mbps)", blank=True, null=True)
    downstream_rate = models.FloatField(verbose_name="下行速率(Mbps)", blank=True, null=True)
    standard = models.CharField(max_length=50, verbose_name="通信制式", blank=True, null=True)
    plmn = models.CharField(max_length=20, verbose_name="运营商PLMN", blank=True, null=True)
    cellid = models.CharField(max_length=20, verbose_name="服务小区CellID", blank=True, null=True)
    pci = models.IntegerField(verbose_name="服务小区PCI", blank=True, null=True)
    rsrp = models.FloatField(verbose_name="RSRP(信号接收功率)", blank=True, null=True)
    sinr = models.FloatField(verbose_name="SINR(信噪比)", blank=True, null=True)
    rssi = models.FloatField(verbose_name="RSSI(信号强度指示)", blank=True, null=True)

    def __str__(self):
        return f"Report from {self.sn} at {self.report_date} {self.report_time}"

    class Meta:
        verbose_name = "端站上报信息"
        verbose_name_plural = "端站上报信息"
        # 定义复合唯一约束，效果等同于复合主键
        unique_together = ('type', 'sn', 'report_date', 'report_time')
        # 可以为经常一起查询的字段创建联合索引
        indexes = [
            models.Index(fields=['sn', 'report_date']),
        ]