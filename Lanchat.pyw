import tkinter as tk
from tkinter import scrolledtext
import threading
import socket

root = tk.Tk()
root.title("LAN Chat Box")

message_area = scrolledtext.ScrolledText(root, wrap=tk.WORD)
message_area.pack(fill=tk.BOTH, expand=True)

input_area = tk.Entry(root)
input_area.pack(fill=tk.X)

def send_message(event):
    message = input_area.get()
    s2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s2.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    # Broadcast address and port
    broadcast_addr = '192.168.1.255'
    port = 12345
    s2.sendto(message.encode('utf-8'), (broadcast_addr, port))
    input_area.delete(0, tk.END)
    

input_area.bind("<Return>", send_message)

def receive_messages():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('', 12345))

    while True:
        data, addr = s.recvfrom(1024)
        message_area.insert(tk.END, f"{addr}: {data.decode()}\n")
        message_area.see("end")
        
receive_thread = threading.Thread(target=receive_messages)
receive_thread.start()

root.mainloop()