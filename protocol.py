"""
protocol.py
Message framing:  [4-byte length][JSON payload]
TCP is a byte stream, so we send the size first, then read exactly that many bytes.
"""
import json
import struct

CHUNK_SIZE = 64 * 1024  # 64 KB chunks for file transfer


def send_message(sock, message):
    """Convert a dict to JSON and send it with a 4-byte length prefix."""
    data = json.dumps(message).encode("utf-8")
    sock.sendall(struct.pack(">I", len(data)) + data)


def recv_exact(sock, size):
    """Keep calling recv() until exactly `size` bytes are received."""
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionError("Peer disconnected")
        data += chunk
    return data


def recv_message(sock):
    """Read the 4-byte length, then read the JSON message and return a dict."""
    header = recv_exact(sock, 4)
    length = struct.unpack(">I", header)[0]
    if length > 1024 * 1024:  # JSON messages are small; protects from garbage data
        raise ValueError("Message too large")
    return json.loads(recv_exact(sock, length).decode("utf-8"))
