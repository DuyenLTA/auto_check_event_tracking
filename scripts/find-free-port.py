#!/usr/bin/env python3
"""In ra cong trong dau tien tu <start> den <start+19>. In 0 neu het.

Tach ra script rieng de start.sh khong phai nhung Python vao chuoi bash.
"""
import socket
import sys


def free(port: int) -> bool:
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


start = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
for candidate in range(start, start + 20):
    if free(candidate):
        print(candidate)
        break
else:
    print(0)
