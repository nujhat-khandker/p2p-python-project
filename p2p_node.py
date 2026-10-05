"""
p2p_node.py
Every peer = TCP Server (accepts connections) + TCP Client (connects to others).
"""
import os
import socket
import threading
import uuid

from protocol import send_message, recv_message, recv_exact, CHUNK_SIZE

DOWNLOAD_DIR = "downloads"


class P2PNode:
    def __init__(self, name, port, log_callback, peers_callback):
        self.name = name
        self.port = port
        self.peer_id = uuid.uuid4().hex[:8]
        self.log = log_callback              # log(text)
        self.peers_changed = peers_callback  # peers_changed()
        self.server_socket = None
        self.running = False
        self.peers = {}                      # peer_id -> dict(name, ip, port, sock, lock)
        self.peers_lock = threading.Lock()
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    # ------------------------------------------------------------ server role
    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("0.0.0.0", self.port))   # raises OSError if port is busy
        self.server_socket.listen()
        self.running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()
        self.log(f"[SYSTEM] Peer started: {self.name} [{self.peer_id}] on port {self.port}")

    def _accept_loop(self):
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
            except OSError:
                break  # server socket closed
            threading.Thread(target=self._handle_incoming, args=(conn, addr), daemon=True).start()

    def _handle_incoming(self, conn, addr):
        """Someone connected to us: receive HELLO, reply HELLO_ACK."""
        try:
            conn.settimeout(5)
            hello = recv_message(conn)
            if hello.get("type") != "hello":
                raise ValueError("Expected hello")
            send_message(conn, {"type": "hello_ack", "peer_id": self.peer_id,
                                "peer_name": self.name, "port": self.port})
            conn.settimeout(None)
        except (OSError, ValueError, ConnectionError) as e:
            self.log(f"[ERROR] Handshake failed with {addr[0]}: {e}")
            conn.close()
            return
        self._register_and_listen(hello["peer_id"], hello["peer_name"], addr[0], hello["port"], conn)

    # ------------------------------------------------------------ client role
    def connect(self, ip, port):
        """We connect to another peer: send HELLO, wait for HELLO_ACK."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((ip, port))
            send_message(sock, {"type": "hello", "peer_id": self.peer_id,
                                "peer_name": self.name, "port": self.port})
            ack = recv_message(sock)
            if ack.get("type") != "hello_ack":
                raise ValueError("Expected hello_ack")
            sock.settimeout(None)
        except (OSError, ValueError, ConnectionError) as e:
            self.log(f"[ERROR] Connection failed: {e}")
            return
        self.log(f"[SYSTEM] Connected to {ack['peer_name']} ({ip}:{port})")
        # listen in a new thread so connect() returns immediately
        threading.Thread(target=self._register_and_listen, daemon=True,
                         args=(ack["peer_id"], ack["peer_name"], ip, ack["port"], sock)).start()

    # ------------------------------------------------------------ connection handling
    def _register_and_listen(self, peer_id, peer_name, ip, port, sock):
        with self.peers_lock:
            if peer_id == self.peer_id or peer_id in self.peers:
                self.log(f"[SYSTEM] Already connected to {peer_name}, extra connection closed")
                sock.close()
                return
            self.peers[peer_id] = {"name": peer_name, "ip": ip, "port": port,
                                   "sock": sock, "lock": threading.Lock()}
        self.peers_changed()
        try:
            while self.running:
                msg = recv_message(sock)
                if msg.get("type") == "text":
                    self.log(f"{msg['sender_name']} -> You: {msg['message']}")
                elif msg.get("type") == "file":
                    self._receive_file(sock, msg)
        except (ConnectionError, OSError, ValueError) as e:
            if self.running:
                self.log(f"[SYSTEM] {peer_name} disconnected ({e})")
        finally:
            self._remove_peer(peer_id)

    def _remove_peer(self, peer_id):
        with self.peers_lock:
            peer = self.peers.pop(peer_id, None)
        if peer:
            try:
                peer["sock"].shutdown(socket.SHUT_RDWR)   # wakes up the listener thread
            except OSError:
                pass
            peer["sock"].close()
            self.peers_changed()

    def get_peers(self):
        with self.peers_lock:
            return [(pid, p["name"], p["ip"], p["port"]) for pid, p in self.peers.items()]

    # ------------------------------------------------------------ text
    def send_text(self, peer_id, text):
        peer = self.peers.get(peer_id)
        if not peer:
            self.log("[ERROR] Peer not connected")
            return
        try:
            with peer["lock"]:
                send_message(peer["sock"], {"type": "text", "sender_id": self.peer_id,
                                            "sender_name": self.name, "message": text})
            self.log(f"You -> {peer['name']}: {text}")
        except OSError as e:
            self.log(f"[ERROR] Could not send to {peer['name']}: {e}")
            self._remove_peer(peer_id)

    # ------------------------------------------------------------ file
    def send_file(self, peer_id, path):
        """Runs in its own thread so the GUI does not freeze on big files."""
        threading.Thread(target=self._send_file, args=(peer_id, path), daemon=True).start()

    def _send_file(self, peer_id, path):
        peer = self.peers.get(peer_id)
        if not peer:
            self.log("[ERROR] Peer not connected")
            return
        if not os.path.isfile(path):
            self.log("[ERROR] File does not exist")
            return
        filename = os.path.basename(path)
        filesize = os.path.getsize(path)
        try:
            with peer["lock"]:
                # 1) metadata
                send_message(peer["sock"], {"type": "file", "sender_id": self.peer_id,
                                            "sender_name": self.name,
                                            "filename": filename, "filesize": filesize})
                # 2) raw bytes in chunks
                with open(path, "rb") as f:
                    while True:
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        peer["sock"].sendall(chunk)
            self.log(f"You -> {peer['name']}: File sent: {filename} ({filesize} bytes)")
        except OSError as e:
            self.log(f"[ERROR] File transfer failed: {e}")
            self._remove_peer(peer_id)

    def _receive_file(self, sock, msg):
        filename = os.path.basename(msg["filename"])   # basename = safe, no folder tricks
        filesize = int(msg["filesize"])
        if filesize < 0:
            raise ValueError("Invalid file size")
        save_path = self._unique_path(filename)
        remaining = filesize
        with open(save_path, "wb") as f:
            while remaining > 0:                        # read EXACTLY filesize bytes
                chunk = sock.recv(min(CHUNK_SIZE, remaining))
                if not chunk:
                    raise ConnectionError("Disconnected during file transfer")
                f.write(chunk)
                remaining -= len(chunk)
        self.log(f"{msg['sender_name']} -> You: File received: {os.path.basename(save_path)}")

    @staticmethod
    def _unique_path(filename):
        """If photo.jpg exists, save as photo_1.jpg, photo_2.jpg ..."""
        path = os.path.join(DOWNLOAD_DIR, filename)
        base, ext = os.path.splitext(filename)
        n = 1
        while os.path.exists(path):
            path = os.path.join(DOWNLOAD_DIR, f"{base}_{n}{ext}")
            n += 1
        return path

    # ------------------------------------------------------------ stop
    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        for pid in list(self.peers):
            self._remove_peer(pid)
        self.log("[SYSTEM] Peer stopped")
