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
├── acu/
│   ├── NM_Service.py      # UDP通信与数据处理服务核心
│   └── EventManager.py    # 事件管理器模块
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
├── utils/
	├── log.py     		   # 日志模块核心文件
│   └── __init__.py        # 全局日志记录器 gl_logger 的定义与配置
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


该表是系统的核心数据表，用于存储所有端站通过UDP上报的状态信息。`NM_Service.py` 模块负责将接收到的数据清洗、转换后存入此表。

| 字段名 (Field Name)  | 数据类型 (Data Type) | 说明                |
| -------------------- | -------------------- | ------------------- |
| **复合唯一约束字段** |                      |                     |                                                           |
| `type`               | `CharField(50)`      | 设备类型名          |
| `sn`                 | `CharField(50)`      | 设备序列号          |
| `report_date`        | `DateField`          | 上报的日期          |
| `report_time`        | `TimeField`          | 上报的具体时间      |
| **操作信息**         |                      |                     |
| `op`                 | `CharField(20)`      | 操作类型            |
| `op_sub`             | `CharField(20)`      | 操作子类            |
| **端站状态信息**     |                      |                     |
| `long`               | `FloatField`         | 端站经度            |
| `lat`                | `FloatField`         | 端站纬度            | 
| `theory_yaw`         | `FloatField`         | 理论方位角          |
| `yaw`                | `FloatField`         | 当前方位角          |
| `pitch`              | `FloatField`         | 当前俯仰角          |
| `roll`               | `FloatField`         | 当前横滚角          |
| `yao_limit_state`    | `CharField(50)`      | 方位限位状态        |
| `temp`               | `FloatField`         | 温度 (°C)           |
| `humi`               | `FloatField`         | 湿度 (%)            |
| **基站相关信息**     |                      |                     |
| `bts_name`           | `CharField(100)`     | 基站名              |
| `bts_long`           | `FloatField`         | 基站经度            |
| `bts_lat`            | `FloatField`         | 基站纬度            |
| `bts_number`         | `CharField(50)`      | 基站编号            |
| `bts_group_number`   | `CharField(50)`      | 基站分区号          |
| `bts_r`              | `FloatField`         | 基站覆盖半径(公里)  |
| **通信质量信息**     |                      |                     |
| `upstream_rate`      | `FloatField`         | 上行速率(Mbps)      |
| `downstream_rate`    | `FloatField`         | 下行速率(Mbps)      |
| `standard`           | `CharField(50)`      | 通信制式            |
| `plmn`               | `CharField(20)`      | 运营商PLMN          |
| `cellid`             | `CharField(20)`      | 服务小区CellID      |
| `pci`                | `IntegerField`       | 服务小区PCI         |
| `rsrp`               | `FloatField`         | RSRP (信号接收功率) |
| `sinr`               | `FloatField`         | SINR (信噪比)       |
| `rssi`               | `FloatField`         | RSSI (信号强度指示) |

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



# UDP通信模块 (`NM_Service.py`) - 技术说明



## 1. 模块概述



`NM_Service.py` 是项目核心的UDP通信服务模块，专用于与外部设备或平台（例如，网管平台）进行数据交互。该模块采用异步、事件驱动的设计模式，实现了网络IO与业务逻辑的解耦，确保了高效、稳定的数据处理能力。

该模块的核心职责包括：

- **监听UDP端口**：在后台线程中持续监听指定的UDP端口（默认为 `58888`），接收上报的数据。
- **数据解析与处理**：对接收到的JSON格式数据进行解码、解析和清洗。
- **数据库集成**：将经过处理的有效数据持久化存储到 Django 项目的 `TerminalReport` 数据表中。
- **数据发送**：提供标准接口，供项目其他部分调用以通过UDP发送消息。



## 2. 技术架构与设计模式



为了实现高效且非阻塞的通信，本模块采用了多种成熟的设计模式：

- **多线程 (Multi-threading)**
  - 一个独立的 **UDP监听线程** (`__udp_loop`) 专门负责网络数据的接收。这使得主线程不会因为等待网络IO而被阻塞。
  - 套接字 (`socket`) 被设置为 **非阻塞模式** (`setblocking(False)`)，即使没有数据到达，`recvfrom` 调用也会立即返回，避免了CPU资源的空转。
- **事件驱动架构 (Event-Driven Architecture)**
  - 引入了 `EventManager` (事件管理器) 作为模块的核心调度器。网络IO操作（接收/发送）与具体的业务逻辑（数据处理/数据库操作）完全分离。
  - 当监听线程收到数据时，它不会直接处理，而是将数据封装成一个 `RECEIVE_NM_DATA` 事件并放入事件队列。
  - `EventManager` 在其自己的工作线程中从队列中取出事件，并调用预先注册的处理器 (`__handle_nm_data`) 来执行业务逻辑，实现了任务的异步处理。
- **Django环境集成**
  - 脚本通过在文件顶部执行特定的初始化代码，成功加载了整个Django项目的配置和环境。
  - 这使得脚本可以直接使用Django强大的ORM（对象关系映射）功能，像在Django内部一样方便地操作数据库模型 (`TerminalReport.objects.create()`)。



## 3. 核心组件与工作流





### 3.1. 初始化 (`__init__`)



当 `NM_Service` 类被实例化时，会执行以下关键初始化步骤：

1. **配置UDP地址**：设置监听的IP地址和端口（例如 `'127.0.0.1:58888'`）。
2. **创建事件管理器**：实例化 `EventManager`，并为其注册两个核心事件的监听器：
   - `Event.RECEIVE_NM_DATA` -> `__handle_nm_data` (处理接收到的数据)
   - `Event.SEND_NM_DATA` -> `__send_to_nm` (处理待发送的数据)
3. **创建监听线程**：创建一个 `Thread` 对象，并将其目标函数设置为 `__udp_loop` 方法。



### 3.2. 服务启动 (`start`)



调用 `start()` 方法会激活整个服务：

1. 启动 `EventManager` 的事件循环线程。
2. 创建UDP套接字，并将其设置为非阻塞模式。
3. 将套接字绑定到预设的IP和端口。
4. 启动UDP监听线程 (`__udp_loop_thread`)。



### 3.3. 数据接收与处理流程



这是一个完整的从数据包到达到底层存储的流程：

Code snippet

```
sequenceDiagram
    participant 外部设备
    participant UDP监听线程 (__udp_loop)
    participant 事件管理器 (EventManager)
    participant 业务处理方法 (__handle_nm_data)
    participant Django ORM

    外部设备->>UDP监听线程 (__udp_loop): 发送UDP数据包 (GBK/UTF-8编码)
    UDP监听线程 (__udp_loop)->>事件管理器 (EventManager): 封装为 RECEIVE_NM_DATA 事件并发送
    事件管理器 (EventManager)-->>业务处理方法 (__handle_nm_data): 从队列取出事件并调用处理器
    业务处理方法 (__handle_nm_data)->>业务处理方法 (__handle_nm_data): 解码 (优先UTF-8, 失败则尝试GBK)
    業務處理方法 (__handle_nm_data)->>業務處理方法 (__handle_nm_data): 解析JSON字符串为Python字典
    业务处理方法 (__handle_nm_data)->>业务处理方法 (__handle_nm_data): 数据清洗与映射 (使用 JSON_TO_MODEL_MAP)
    业务处理方法 (__handle_nm_data)->>业务处理方法 (__handle_nm_data): 类型转换 (如 "N/A" -> None)
    业务处理方法 (__handle_nm_data)->>Django ORM: 调用 TerminalReport.objects.create()
    Django ORM->>Django ORM: 验证数据并生成SQL语句
    Django ORM-->>数据库: 执行 INSERT 操作
```



### 3.4. 核心数据处理方法 (`__handle_nm_data`)



这是模块的业务逻辑核心，负责将原始消息转化为结构化的数据库记录。

1. **智能解码**：为了增强兼容性，代码会首先尝试使用标准的 `UTF-8` 解码。如果失败（通常因为中文字符使用了不同编码），它会自动回退并尝试使用 `GBK` 解码。
2. **字段映射**：定义了一个关键的 `JSON_TO_MODEL_MAP` 字典，用于将消息中的键名（可能不规范）映射到数据库模型中标准的字段名。这使得代码非常灵活，当消息格式变化时，只需修改此字典即可。
3. **数据清洗与转换**：
   - **特殊值处理**：将消息中表示“无数据”的字符串（如 `"N/A"`）智能地转换成 Python 的 `None`，以便数据库能正确存为 `NULL`。
   - **类型强制转换**：通过 `isinstance` 检查模型字段的目标类型，自动将接收到的数字等值转换为字符串，以匹配 `CharField` 类型的字段要求。
4. **数据持久化**：使用 `TerminalReport.objects.create(**model_data)` 将清洗和转换后的数据字典直接解包作为参数，高效地创建一条新的数据库记录。



## 4. 如何配置与运行





### 4.1. Django环境接入



脚本的开头部分是其能够独立于 `manage.py` 运行，同时又能利用Django功能的关键。

Python

```
# --- Start of Django Setup ---
import os
import sys
import django

# 将项目根目录 'MBP' 添加到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# 设置Django设置模块路径
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mbp_project.settings') 
django.setup()
# --- End of Django Setup ---
```

这段代码确保了在导入任何Django模型之前，Django环境已被正确加载。



### 4.2. 字段映射配置



您可以根据实际接收到的消息格式，灵活地修改 `JSON_TO_MODEL_MAP` 字典。

Python

```
# 示例：如果消息中的序列号键名是 "device_sn"，而模型中是 "sn"
JSON_TO_MODEL_MAP = {
    'device_sn': 'sn',
    # ... 其他映射规则
}
```



### 4.3. 运行服务



由于该服务依赖于Django环境，**强烈建议**通过自定义Django管理命令来启动。

1. **创建管理命令文件**： 在 `terminal_management/management/commands/` 目录下创建 `start_nm_service.py` 文件。

2. **启动服务**： 在项目根目录下，运行以下命令即可启动UDP服务：

   Bash

   ```
   python manage.py start_nm_service
   ```

   服务将在后台持续运行，监听UDP端口，并将接收到的数据实时存入数据库。