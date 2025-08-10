# MBP/test_req_res.py
# 该文件仅用于测试响应机制流程，不包含实际业务逻辑

import threading
import time
import socket
from json import loads, dumps

# 关键：从 acu 文件夹中导入您的 NM_Service 类
# 脚本会自动加载Django环境，因为 NM_Service.py 内部已经处理了
from acu.NM_Service import NM_Service

# --- 全局配置 ---
# 我们的服务监听的地址和端口
SERVICE_HOST = '127.0.0.1'
SERVICE_PORT = 58888

# 我们模拟的“端站设备”监听的地址和端口
DEVICE_HOST = '127.0.0.1'
DEVICE_PORT = 58889  # 注意：使用一个不同的端口

# 创建一个全局的 NM_Service 实例，供测试使用
# 这样我们就不需要在线程间传递实例了
nm_service = NM_Service()

# --- 模拟端站设备 ---
def simulate_device():
    """
    这个函数运行在自己的线程里，模拟一个UDP端站设备。
    它接收请求，并发送响应。
    """
    # 创建一个UDP套接字来监听发给它的请求
    device_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    device_socket.bind((DEVICE_HOST, DEVICE_PORT))
    print(f"[设备端] 模拟设备已启动，正在监听 {DEVICE_HOST}:{DEVICE_PORT}")

    try:
        # 只处理一个请求然后退出
        data, addr = device_socket.recvfrom(4096)
        
        # 将收到的字节数据解码并解析成JSON
        request_dict = loads(data.decode('utf-8'))
        print(f"[设备端] 收到来自 {addr} 的请求: {request_dict}")

        # --- 构造响应 ---
        # 核心：必须包含与请求中完全相同的 'request_id'
        response_data = {
            "request_id": request_dict.get('request_id'),
            "status": "success",
            "message": "请求已成功处理",
            "device_temp": 42.5,
            "signal_strength": -85
        }
        
        print(f"[设备端] 准备发送响应: {response_data}")
        time.sleep(1) # 模拟处理耗时

        # 将响应发送回我们的 NM_Service 服务
        device_socket.sendto(dumps(response_data).encode('utf-8'), (SERVICE_HOST, SERVICE_PORT))
        print("[设备端] 响应已发送。")

    finally:
        device_socket.close()
        print("[设备端] 模拟设备已关闭。")

# --- 模拟请求发起方 ---
def start_client_request():
    """
    这个函数模拟一个客户端（例如，您的Web后台任务）。
    它调用阻塞方法来获取数据。
    """
    print("\n[客户端] 等待2秒，确保服务完全启动...")
    time.sleep(2)

    print("[客户端] 准备发起一个 'get_status' 请求...")
    request_payload = {
        'op': 'query',
        'op_sub': 'get_status',
        'target': 'all'
    }

    # 调用我们新添加的核心方法！
    response = nm_service.send_request_and_wait(
        peer_ip=DEVICE_HOST,
        peer_port=DEVICE_PORT,
        request_data=request_payload,
        timeout=5.0  # 设置5秒超时
    )

    print("\n----------- 测试结果 -----------")
    if response:
        print(f"✅ [客户端] 成功！收到的响应: {response}")
    else:
        print(f"❌ [客户端] 失败！请求超时或发生错误。")
    print("--------------------------------")


# --- 主测试流程 ---
if __name__ == '__main__':
    print("--- 启动UDP请求/响应功能集成测试 ---")

    # 1. 启动我们的 NM_Service 服务
    # 因为它内部有自己的线程，所以不会阻塞主线程
    nm_service.start()
    print("[主流程] NM_Service 已启动。")

    # 2. 在一个新线程中启动模拟设备
    device_thread = threading.Thread(target=simulate_device)
    device_thread.start()

    # 3. 在主线程中，调用客户端发起请求的函数
    # 这个函数会阻塞，直到收到响应或超时
    start_client_request()

    # 4. 清理工作
    print("[主流程] 测试完成，正在停止服务...")
    nm_service.stop()
    device_thread.join() # 等待设备线程完全结束
    print("[主流程] 所有组件已安全关闭。")