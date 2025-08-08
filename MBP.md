# 船舶端站管理系统 (MBP) - 技术文档

## 1. 项目概述

船舶端站管理系统（MBP）是一个基于 Django 框架开发的 Web 应用，旨在提供对船舶、船载端站及地面基站基础信息的集中管理（CRUD）功能。

本项目最大的技术特点是集成了 **Django Channels**，实现了基于 WebSocket 的实时数据更新机制。当后台数据库发生任何（增、删、改）变化时，前端所有打开的列表页面都会收到通知并自动刷新，确保数据的一致性和实时性。

本文档旨在为后续的开发及维护人员提供清晰的技术指引。

## 2. 技术栈

* **后端框架**: Django
* **异步与WebSocket**: Django Channels
* **消息队列/信道层**: Redis
* **数据库**: MySQL
* **前端框架**: Bootstrap 5
* **运行环境**: Python, Daphne (ASGI 服务器)

## 3. 项目文件结构

项目主要由一个 Django 项目配置目录 `mbp_project` 和一个核心应用 `terminal_management` 组成。

```
mbp-project/
├── mbp_project/           # Django 项目配置目录
│   ├── asgi.py            # ASGI 服务器入口，处理 HTTP 和 WebSocket 路由
│   ├── settings.py        # 项目总配置文件
│   ├── urls.py            # 项目主路由文件
│   └── wsgi.py            # WSGI 服务器入口 (未使用)
├── terminal_management/   # 核心应用目录
│   ├── migrations/        # 数据库迁移文件
│   ├── templates/         # HTML 模板目录 (实际位于项目根目录)
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py            # App 配置文件，用于注册信号
│   ├── consumers.py       # WebSocket 消费者
│   ├── forms.py           # Django 表单定义
│   ├── models.py          # 数据库模型定义
│   ├── routing.py         # WebSocket 路由
│   ├── services.py        # 业务逻辑层
│   ├── signals.py         # 信号处理器，用于触发实时更新
│   ├── urls.py            # App 级路由文件
│   └── views.py           # 视图函数
├── templates/             # 项目级模板目录
│   ├── base.html          # 基础模板
│   ├── ship_list.html     # 船舶列表
│   └── ... (其他模板文件)
├── manage.py              # Django 命令行工具
└── ...
```

## 4. 核心组件详解

### 4.1. 数据库模型 (`terminal_management/models.py`)

数据库是本系统的核心，共包含四个主要模型。

#### 4.1.1. `ShipInfo` - 船舶信息表

存储船舶的基础信息。

| 字段名       | 字段类型         | 说明                               |
| :----------- | :--------------- | :--------------------------------- |
| `mmsi`       | `CharField(9)`   | **主键**。海上移动通信业务标识码。 |
| `ship_name`  | `CharField(100)` | 船名。                             |
| `call_sign`  | `CharField(20)`  | **唯一, 索引**。船舶呼号。         |
| `ship_owner` | `CharField(100)` | 船东 (可为空)。                    |

#### 4.1.2. `TerminalInfo` - 端站信息表

存储安装在船舶上的端站设备信息。

| 字段名        | 字段类型                | 说明                                          |
| :------------ | :---------------------- | :-------------------------------------------- |
| `sn`          | `CharField(50)`         | **主键**。设备序列号 (SN)。                   |
| `ship`        | `ForeignKey`            | **外键**。关联到 `ShipInfo` 的主键 (`mmsi`)。 |
| `ip_address`  | `GenericIPAddressField` | IP 地址 (可为空)。                            |
| `port_number` | `PositiveIntegerField`  | 端口号 (可为空)。                             |

#### 4.1.3. `BaseStationInfo` - 基站信息表

存储地面基站的技术参数。

| 字段名              | 字段类型         | 说明                          |
| :------------------ | :--------------- | :---------------------------- |
| `bts_id`            | `CharField(50)`  | **主键**。基站ID。            |
| `bts_name`          | `CharField(100)` | **唯一**。基站名称。          |
| `coverage_distance` | `FloatField`     | 覆盖距离，单位公里 (可为空)。 |
| `region_code`       | `CharField(50)`  | 地区号 (可为空)。             |
| `longitude`         | `FloatField`     | 站点经度 (可为空)。           |
| `latitude`          | `FloatField`     | 站点纬度 (可为空)。           |

#### 4.1.4. `TerminalReport` - 端站上报信息表

用于记录端站设备上报的各类状态和参数，是系统的核心日志数据。

| 字段名 | 字段类型 | 说明 |
| :--- | :--- | :--- |
| `id` | `BigAutoField` | **自增主键**。由 Django 自动创建，用于唯一标识每一条上报记录。 |
| `type` | `IntegerField` | 设备类型号。与 sn, date, time 构成复合唯一约束。 |
| `sn` | `CharField(50)` | 设备序列号。已创建**数据库索引**以优化查询速度。 |
| `report_date` | `DateField` | 上报日期。已创建**数据库索引**以优化查询速度。 |
| `report_time` | `TimeField` | 上报时间。 |
| `op` | `IntegerField` | 操作类型。 |
| `op_sub` | `IntegerField` | 操作子类。 |
| `long` | `FloatField` | 端站当前的经度 (可为空)。 |
| `lat` | `FloatField` | 端站当前的纬度 (可为空)。 |
| `theory_yaw`| `FloatField` | 理论方位角 (可为空)。 |
| `yaw` | `FloatField` | 当前方位角 (可为空)。 |
| `pitch` | `FloatField` | 当前俯仰角 (可为空)。 |
| `roll` | `FloatField` | 当前横滚角 (可为空)。 |
| `yao_limit_state` | `CharField(50)` | 方位限位状态 (可为空)。 |
| `temp` | `FloatField` | 温度，单位 °C (可为空)。 |
| `humi` | `FloatField` | 湿度，单位 % (可为空)。 |
| `bts_name` | `CharField(100)`| 所连接的基站名 (可为空)。 |
| `bts_long` | `FloatField` | 所连接的基站经度 (可为空)。 |
| `bts_lat` | `FloatField` | 所连接的基站纬度 (可为空)。 |
| `bts_r` | `FloatField` | 所连接的基站覆盖半径，单位公里 (可为空)。 |
| `bts_number` | `CharField(50)` | **(新增)** 基站编号 (可为空)。 |
| `bts_group_number`| `CharField(50)` | **(新增)** 基站分区号 (可为空)。 |
| `dgps_err` | `CharField(50)` | **(新增)** DGPS差分状态 (可为空)。 |
| `dgps_start` | `CharField(50)` | **(新增)** DGPS启动状态 (可为空)。 |
| `upstream_rate`| `FloatField` | 上行速率，单位 Mbps (可为空)。 |
| `downstream_rate`| `FloatField` | 下行速率，单位 Mbps (可为空)。 |
| `standard` | `CharField(50)` | 通信制式 (可为空)。 |
| `plmn` | `CharField(20)` | 运营商PLMN码 (可为空)。 |
| `cellid` | `CharField(20)` | 服务小区CellID (可为空)。 |
| `pci` | `IntegerField` | 服务小区PCI (可为空)。 |
| `rsrp` | `FloatField` | RSRP (信号接收功率) (可为空)。 |
| `sinr` | `FloatField` | SINR (信噪比) (可为空)。 |
| `rssi` | `FloatField` | RSSI (信号强度指示) (可为空)。 |

**复合唯一约束**: (`type`, `sn`, `report_date`, `report_time`)。

### 4.2. 业务逻辑层 (`terminal_management/services.py`)

为了实现业务逻辑与视图逻辑的解耦，项目中定义了 `services.py` 文件。所有数据库的查询和操作都被封装在此文件中。

* **统一返回格式**: 所有 service 函数都遵循 `(success, result_or_error)` 的元组返回格式，其中 `success` 是布尔值，第二个元素是成功时的对象或失败时的错误信息字符串。
* **事务处理**: 所有写操作（创建、更新、删除）都使用了 `transaction.atomic()` 来确保数据库操作的原子性。

### 4.3. 表单处理 (`terminal_management/forms.py`)

所有的数据录入和编辑都通过 Django Forms 进行处理和验证。

* **模型表单**: 所有表单（`ShipInfoForm`, `TerminalInfoForm`, `BaseStationInfoForm`）都继承自 `forms.ModelForm`，直接与数据库模型对应。
* **动态 `__init__`**: 通过重写 `__init__` 方法，实现了在**编辑模式**下将主键字段设置为只读 (`readonly`) 且非必填 (`required=False`)，防止了误操作和验证错误。在**新建模式**下，为主键字段添加了占位提示文本。
* **自定义验证**: 通过 `clean_<field_name>` 方法，为所有设置了 `unique=True` 的字段（如 `call_sign`, `bts_name`）实现了**排除自身的唯一性验证**，解决了编辑时保存数据会误报“字段已存在”的经典问题。

### 4.4. 实时通信 (WebSocket)

实时通信是本项目的核心功能，由 Django Channels 驱动，涉及以下几个文件：

* **`mbp_project/asgi.py`**: 作为 ASGI 应用的入口，它是一个 `ProtocolTypeRouter`，负责将传入的连接根据协议类型（`http` 或 `websocket`）分发给不同的处理程序。
* **`terminal_management/routing.py`**: 定义了 WebSocket 的 URL 路由。`path('ws/data/', ...)` 将所有到此路径的 WebSocket 连接都指向 `DataConsumer`。
* **`terminal_management/consumers.py`**: 定义了 `DataConsumer`。当一个客户端连接时，它会被添加到一个名为 `'data_updates'` 的组（Group）中。当这个组收到消息时，`DataConsumer` 会将消息通过 WebSocket 推送给它所连接的客户端。
* **`terminal_management/signals.py`**: **实时更新的触发器**。它利用 Django 的 `post_save` 和 `post_delete` 信号，监听所有模型的保存和删除操作。一旦操作发生，对应的信号处理器（例如 `ship_update_handler`）就会被触发，并通过 Channels 的信道层 (`channel_layer`) 向 `'data_updates'` 组广播一条包含更新内容的消息。
* **`templates/base.html`**: 包含了客户端的 JavaScript 代码。这段代码负责建立到 `/ws/data/` 的 WebSocket 连接。当收到来自服务器的消息时，它会检查用户当前是否在列表页。如果是，则执行 `location.reload()` 刷新页面；如果用户在表单页，则不执行任何操作，等待服务器的 `redirect` 指令，从而避免了指令冲突。

### 4.5. 视图与模板

* **视图 (`views.py`)**: 遵循标准的 Django 函数式视图（FBV）模式，所有需要登录的视图都使用了 `@login_required` 装饰器。视图函数负责接收请求，处理表单，调用 `services.py` 中的业务逻辑，并渲染最终的 HTML 页面。
* **URL (`urls.py`)**: 采用了两级路由。项目主路由 `mbp_project/urls.py` 将所有请求 `include` 到 `terminal_management/urls.py` 中进行处理。
* **模板 (`templates/`)**: 使用了 Django 的模板继承机制，所有页面都继承自 `base.html`。`base.html` 提供了统一的导航栏、侧边栏和页面布局。

## 5. 项目部署与运行

### 5.1. 环境依赖

* Python
* Django
* Channels
* channels_redis
* MySQL 数据库
* Redis 服务器

### 5.2. 安装与配置

1.  安装所有 Python 依赖。
2.  在 `mbp_project/settings.py` 中配置 `DATABASES` 以连接到您的 MySQL 实例。
3.  确保 Redis 服务正在运行，并在 `settings.py` 中配置 `CHANNEL_LAYERS` 的 `hosts` 地址。

### 5.3. 运行项目

1.  **数据库迁移**:
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

2.  **启动服务**:
    由于项目使用了 Django Channels，不能使用标准的 `runserver` 命令。必须使用 ASGI 服务器，如 Daphne：
    ```bash
    daphne -p 8000 mbp_project.asgi:application
    ```
    服务器将在 `8000` 端口上运行，同时处理 HTTP 和 WebSocket 请求。