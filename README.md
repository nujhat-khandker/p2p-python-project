
# CSE 433: Peer-to-Peer Network Communication & File Sharing

# Project Overview
This project is a lightweight, decentralized Peer-to-Peer (P2P) network application written in Python using Tkinter for GUI and standard TCP sockets for networking. 

In this application, there is no central server. Every running instance acts as both a TCP Server (to accept incoming connections) and a TCP Client (to initiate outgoing connections). Connected peers can directly exchange text messages and binary files (PDFs, Images, Audio, Documents, etc.) over the local network or on the same machine.

 
# Features
*Decentralized P2P Architecture:*Direct node-to-node communication using TCP sockets without any central server.
*Bi-directional Roles:* Every peer acts as both a Server and a Client simultaneously.
*Handshake Protocol:* Automatic exchange of `hello` and `hello_ack` messages upon connection to set up peer identity.
*Threaded Multi-Peer Support:* Non-blocking multi-threading allowing concurrent connections with multiple peers.
*Custom Message Framing:* Fixed-header 4-byte length framing over TCP byte streams to handle structural message limits.
*Binary File Transfer:* Chunked binary transfer (64 KB chunks) for transferring large files (Images, PDFs, Audios, Videos, ZIPs).
*Auto-renaming Files:* Unique file saving strategy in the `downloads/` directory to prevent accidental overwrites.
*User-Friendly GUI:* Simple Tkinter interface with dynamic peer listings and event logs.

---

## Requirements
- **Python Version:** Python 3.9 or later (Tkinter comes pre-installed on Windows/macOS; on Linux run: `sudo apt install python3-tk`)
- **Third-Party Libraries:** None (Uses standard built-in modules: `socket`, `threading`, `json`, `struct`, `queue`, `tkinter`).

---

## Project Structure
```text
P2P_Network/
├── main.py            # Tkinter GUI implementation & user interaction
├── p2p_node.py        # Core network engine (Server, Client, Threads, File transfer)
├── protocol.py        # Message framing protocol (4-byte length prefix + JSON)
├── requirements.txt   # Dependencies list (Pure Python built-ins)
├── downloads/         # Storage folder for received files
├── screenshots/       # Project testing screenshots
└── README.md          # Setup instructions and documentation

---

## How to Run the Application

Open a terminal or command prompt inside the project directory and execute:

```bash
python main.py

To test with multiple peers, open multiple terminal windows and run the command in each window.

---

## Operating Instructions & Connection Guide

### Test 1: Connecting Two Peers on the Same Computer (Localhost)
1. **Peer 1 (e.g., Nujhat):**
   - Name: `Nujhat`
   - Port: `5001`
   - Click **Start Peer**.
2. **Peer 2 (e.g., xyz):**
   - Name: `xyz`
   - Port: `5004`
   - Click **Start Peer**.
3. **Establish Connection:**
   - In Peer 2 (`xyz`'s window), set IP to `127.0.0.1` and Port to `5001`.
   - Click **Connect**.
   - Both windows will list each other in the **Connected Peers** box.

---

### Test 2: Connecting Peers over the Same Wi-Fi Network (LAN)
1. **Find LAN IP:** Check the local IP address on Computer A (e.g., `192.168.132.43` or `192.168.132.123`).
2. **Start Peer on Computer A (e.g., Alice):**
   - Name: `Alice`
   - Port: `5000`
   - Click **Start Peer**.
3. **Connect from Computer B (e.g., Nujhat):**
   - Name: `Nujhat`
   - Port: `5005`
   - Click **Start Peer**.
   - Enter IP: `192.168.132.43` and Port: `5000`.
   - Click **Connect**.

---

### Test 3: How to Send Text Messages
1. Select the target peer from the **Connected Peers** list.
2. Type your message in the bottom entry box.
3. Press **Enter** or click **Send**.

---

### Test 4: How to Transfer Files
1. Select the target peer from the **Connected Peers** list.
2. Click **Choose File & Send**.
3. Choose any file (`.jpg`, `.png`, `.pdf`, `.mp3`, `.ogg`, `.zip`, etc.) from the file dialog.
4. The receiver will store the file under the `downloads/` directory.

---

## Protocol & Framing Architecture

TCP treats communication as a continuous byte stream without boundary detection. The application utilizes custom application-layer framing to handle message boundaries:

1. **Length-Prefixed Framing:**
   Every control and meta-message is transmitted as:
   `[4-Byte Big-Endian Integer Header (Length)] + [JSON Payload]`

2. **Handshake Sequence:**
   - Initiator sends: `{"type": "hello", "peer_id": "<id>", "peer_name": "<name>", "port": <port>}`
   - Receiver responds: `{"type": "hello_ack", "peer_id": "<id>", "peer_name": "<name>", "port": <port>}`

3. **File Transfer Sequence:**
   - **Step 1 (Metadata):** Header contains `{"type": "file", "filename": "sample.pdf", "filesize": 251391}`
   - **Step 2 (Raw Bytes Stream):** Transmission of exactly `filesize` bytes in chunks of `64 KB` (`65536 bytes`).

---

## Operational Logs & Verification

The system gracefully handles duplicates, network disconnects, and concurrent multi-file transfers as shown in operational logs:

### Localhost Peer Connection & Duplicate Connection Handling
```text
[SYSTEM] Peer started: xyz [405b620e] on port 5004
[SYSTEM] Connected to Nujhat (127.0.0.1:5001)
[SYSTEM] Already connected to Nujhat, extra connection closed
You -> Nujhat: hello
You -> Nujhat: File sent: WhatsApp Image 2025-02-16 at 16.46.34_e818fcb5.jpg (75216 bytes)
 
