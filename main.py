"""
main.py - Tkinter GUI for the P2P application.
Run:  python main.py
"""
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from p2p_node import P2PNode


class App:
    def __init__(self, root):
        self.root = root
        self.node = None
        self.events = queue.Queue()   # network threads put events here, GUI reads them
        self.peer_ids = []            # same order as the listbox
        root.title("UAP P2P Network")
        root.geometry("900x600")
        self.build_ui()
        self.poll_events()
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------------------------------------------------------------- UI
    def build_ui(self):
        # --- My Peer
        f1 = ttk.LabelFrame(self.root, text="My Peer")
        f1.pack(fill="x", padx=8, pady=4)
        ttk.Label(f1, text="Name:").grid(row=0, column=0, padx=4, pady=4)
        self.name_entry = ttk.Entry(f1, width=18)
        self.name_entry.insert(0, "Alice")
        self.name_entry.grid(row=0, column=1)
        ttk.Label(f1, text="Port:").grid(row=0, column=2, padx=4)
        self.port_entry = ttk.Entry(f1, width=8)
        self.port_entry.insert(0, "5000")
        self.port_entry.grid(row=0, column=3)
        self.start_btn = ttk.Button(f1, text="Start Peer", command=self.start_peer)
        self.start_btn.grid(row=0, column=4, padx=6)
        self.stop_btn = ttk.Button(f1, text="Stop", command=self.stop_peer, state="disabled")
        self.stop_btn.grid(row=0, column=5)
        self.info_label = ttk.Label(f1, text="Peer not started")
        self.info_label.grid(row=1, column=0, columnspan=6, sticky="w", padx=4, pady=2)

        # --- Connect
        f2 = ttk.LabelFrame(self.root, text="Connect to Another Peer")
        f2.pack(fill="x", padx=8, pady=4)
        ttk.Label(f2, text="IP:").grid(row=0, column=0, padx=4, pady=4)
        self.ip_entry = ttk.Entry(f2, width=18)
        self.ip_entry.insert(0, "127.0.0.1")
        self.ip_entry.grid(row=0, column=1)
        ttk.Label(f2, text="Port:").grid(row=0, column=2, padx=4)
        self.rport_entry = ttk.Entry(f2, width=8)
        self.rport_entry.insert(0, "5001")
        self.rport_entry.grid(row=0, column=3)
        ttk.Button(f2, text="Connect", command=self.connect_peer).grid(row=0, column=4, padx=6)

        # --- Peers list + log
        f3 = ttk.Frame(self.root)
        f3.pack(fill="both", expand=True, padx=8, pady=4)
        left = ttk.LabelFrame(f3, text="Connected Peers")
        left.pack(side="left", fill="y")
        self.peer_list = tk.Listbox(left, width=32, exportselection=False)
        self.peer_list.pack(fill="both", expand=True, padx=4, pady=4)
        right = ttk.LabelFrame(f3, text="Messages / Events")
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))
        self.log_box = tk.Text(right, state="disabled", font=("Courier", 10))
        self.log_box.pack(fill="both", expand=True, padx=4, pady=4)

        # --- Send text
        f4 = ttk.LabelFrame(self.root, text="Send Text")
        f4.pack(fill="x", padx=8, pady=4)
        self.msg_entry = ttk.Entry(f4)
        self.msg_entry.pack(side="left", fill="x", expand=True, padx=4, pady=4)
        self.msg_entry.bind("<Return>", lambda e: self.send_text())
        ttk.Button(f4, text="Send", command=self.send_text).pack(side="right", padx=4)

        # --- Send file
        f5 = ttk.LabelFrame(self.root, text="Send File")
        f5.pack(fill="x", padx=8, pady=4)
        ttk.Label(f5, text="Text, image, audio, video, PDF, ZIP, etc.").pack(side="left", padx=4)
        ttk.Button(f5, text="Choose File & Send", command=self.send_file).pack(side="right", padx=4, pady=4)

    # ---------------------------------------------------------------- thread-safe events
    def post_log(self, text):          # called from network threads
        self.events.put(("log", text))

    def post_peers(self):              # called from network threads
        self.events.put(("peers", None))

    def poll_events(self):             # runs in GUI thread every 100 ms
        while not self.events.empty():
            kind, data = self.events.get()
            if kind == "log":
                self.log_box.config(state="normal")
                self.log_box.insert("end", data + "\n")
                self.log_box.see("end")
                self.log_box.config(state="disabled")
            elif kind == "peers":
                self.refresh_peers()
        self.root.after(100, self.poll_events)

    def refresh_peers(self):
        self.peer_list.delete(0, "end")
        self.peer_ids = []
        if self.node:
            for pid, name, ip, port in self.node.get_peers():
                self.peer_list.insert("end", f"{name} [{pid}] {ip}:{port}")
                self.peer_ids.append(pid)

    def selected_peer(self):
        sel = self.peer_list.curselection()
        if not sel:
            messagebox.showwarning("No peer selected", "Please select a peer from the list first.")
            return None
        return self.peer_ids[sel[0]]

    # ---------------------------------------------------------------- button actions
    def start_peer(self):
        name = self.name_entry.get().strip()
        try:
            port = int(self.port_entry.get())
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid port (use 1-65535)")
            return
        if not name:
            messagebox.showerror("Error", "Please enter a peer name")
            return
        self.node = P2PNode(name, port, self.post_log, self.post_peers)
        try:
            self.node.start()
        except OSError as e:
            self.node = None
            messagebox.showerror("Error", f"Could not start peer: {e}")
            return
        self.info_label.config(text=f"{name} | ID: {self.node.peer_id} | Port: {port}")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

    def stop_peer(self):
        if self.node:
            self.node.stop()
            self.node = None
        self.refresh_peers()
        self.info_label.config(text="Peer not started")
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def connect_peer(self):
        if not self.node:
            messagebox.showwarning("Error", "Start your peer first")
            return
        ip = self.ip_entry.get().strip()
        try:
            port = int(self.rport_entry.get())
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid port")
            return
        self.node.connect(ip, port)

    def send_text(self):
        if not self.node:
            messagebox.showwarning("Error", "Start your peer first")
            return
        pid = self.selected_peer()
        text = self.msg_entry.get().strip()
        if pid and text:
            self.node.send_text(pid, text)
            self.msg_entry.delete(0, "end")

    def send_file(self):
        if not self.node:
            messagebox.showwarning("Error", "Start your peer first")
            return
        pid = self.selected_peer()
        if not pid:
            return
        path = filedialog.askopenfilename()
        if path:
            self.node.send_file(pid, path)

    def on_close(self):
        if self.node:
            self.node.stop()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
