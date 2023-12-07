import socket

def get_local_ip():
    try:
        # 创建一个临时的套接字来帮助确定本地IP地址
        # 这里使用的是 Google 的公共 DNS 服务器地址
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception as e:
        return "无法确定本地IP: " + str(e)

# 打印局域网中的 IP 地址
print(get_local_ip())



