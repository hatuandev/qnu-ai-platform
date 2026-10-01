import socket

for port in [8001, 8000, 3000, 3001, 5432]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    result = s.connect_ex(('127.0.0.1', port))
    status = "OPEN / LISTENING" if result == 0 else f"CLOSED ({result})"
    print(f"Port {port}: {status}")
    s.close()
