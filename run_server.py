# run_server.py
import os
import uvicorn

if __name__ == "__main__":
    # Uvicorn 是一个高性能的ASGI服务器，Daphne也可以，Uvicorn更常用于开发
    # 'mbp_project.asgi:application' 指向您项目的ASGI入口
    # host="0.0.0.0" 允许局域网其他设备访问
    # reload=True 开启热重载，修改代码后服务器会自动重启
    uvicorn.run(
        'mbp_project.asgi:application',
        host="0.0.0.0",
        port=8000,
        reload=True
    )