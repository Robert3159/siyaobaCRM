#!/usr/bin/env python
"""
CRM Backend 启动脚本

使用方法:
    python start.py              # 使用默认端口 (尝试 8000 -> 8026 -> 3000)
    python start.py 8080         # 指定端口
    python start.py --port=8080 # 使用参数形式
    
环境变量:
    PORT=8080 python start.py   # 通过环境变量指定端口
"""

import os
import sys
import socket
import argparse
import uvicorn


def find_available_port(start_port: int = 8000, max_attempts: int = 10) -> int:
    """
    查找可用端口
    
    Args:
        start_port: 起始端口
        max_attempts: 最大尝试次数
    
    Returns:
        可用的端口号
    """
    ports_to_try = [start_port] + [start_port + i for i in range(1, max_attempts)]
    
    for port in ports_to_try:
        if is_port_available(port):
            return port
    
    # 如果都不可用，返回最后一个尝试的端口（让用户看到错误）
    return ports_to_try[-1]


def is_port_available(port: int) -> bool:
    """检查端口是否可用"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', port))
            return True
    except OSError:
        return False


def save_port_to_file(port: int):
    """将端口保存到文件，供前端读取"""
    port_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.port')
    with open(port_file, 'w') as f:
        f.write(str(port))
    print(f"端口已保存到: {port_file}")


def get_port_from_args() -> int | None:
    """从命令行参数获取端口"""
    parser = argparse.ArgumentParser(description='CRM Backend 启动脚本')
    parser.add_argument('--port', '-p', type=int, help='指定端口号')
    parser.add_argument('port_positional', nargs='?', type=int, help='端口号（位置参数）')
    
    args = parser.parse_args()
    
    # 优先使用 --port 参数
    if args.port:
        return args.port
    
    # 其次使用位置参数
    if args.port_positional:
        return args.port_positional
    
    return None


def get_port_from_env() -> int | None:
    """从环境变量获取端口"""
    port = os.environ.get('PORT') or os.environ.get('BACKEND_PORT')
    if port:
        try:
            return int(port)
        except ValueError:
            print(f"警告: 环境变量中的端口 '{port}' 无效，将使用默认端口")
    return None


def main():
    """主函数"""
    print("=" * 50)
    print("CRM Backend 启动中...")
    print("=" * 50)
    
    # 1. 尝试从命令行参数获取端口
    port = get_port_from_args()
    
    # 2. 尝试从环境变量获取端口
    if port is None:
        port = get_port_from_env()
    
    # 3. 如果都没有指定，尝试查找可用端口
    if port is None:
        # 尝试默认端口 8000
        if is_port_available(8000):
            port = 8000
        # 如果 8000 不可用，尝试 8026
        elif is_port_available(8026):
            port = 8026
        # 如果都不可用，查找可用端口
        else:
            port = find_available_port(8000)
            print(f"注意: 8000 和 8026 端口不可用，已自动选择端口: {port}")
    
    # 验证端口是否真的可用
    if not is_port_available(port):
        print(f"\n错误: 端口 {port} 当前不可用")
        print("尝试查找其他可用端口...")
        port = find_available_port(3000)
        if not is_port_available(port):
            print(f"错误: 无法找到可用端口")
            sys.exit(1)
    
    # 保存端口到文件，供前端读取
    save_port_to_file(port)
    
    # 启动服务器
    print(f"后端服务将在 http://127.0.0.1:{port} 启动")
    print(f"API 地址: http://127.0.0.1:{port}/api")
    print(f"前端代理需要配置: VITE_SERVICE_BASE_URL=http://localhost:{port}/api")
    print("=" * 50)
    print("按 Ctrl+C 停止服务")
    print("=" * 50)
    
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=port,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
