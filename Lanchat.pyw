import tkinter as tk
from tkinter import filedialog
import socket
from PIL import Image, ImageTk
import io
import threading

# Configuration
UDP_IP = '192.168.1.255'  # Broadcast address, adjust as needed
UDP_PORT = 12345
CHUNK_SIZE = 65507  # Max UDP payload size minus protocol overhead

# Get local IP address
LOCAL_IP = socket.gethostbyname(socket.gethostname())

# Function to send text messages
def send_message(event=None):
    message = entry.get()
    if message:
        sock.sendto(message.encode(), (UDP_IP, UDP_PORT))
        entry.delete(0, tk.END)

# Function to open file dialog and send image
def send_image():
    file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
    if file_path:
        send_image_over_udp(file_path)

# Function to send image over UDP
def send_image_over_udp(image_path):
    try:
        # Open image and convert to byte stream
        image = Image.open(image_path)
        with io.BytesIO() as byte_stream:
            image.save(byte_stream, format='PNG')
            byte_data = byte_stream.getvalue()

        # Split byte_data into chunks
        total_chunks = (len(byte_data) + CHUNK_SIZE - 1) // CHUNK_SIZE
        for i in range(total_chunks):
            start = i * CHUNK_SIZE
            end = start + CHUNK_SIZE
            chunk = byte_data[start:end]
            chunk_header = f'IMG_CHUNK_{i}_{total_chunks}'.encode()
            packet = chunk_header + b'\n' + chunk
            try:
                sock.sendto(packet, (UDP_IP, UDP_PORT))
            except Exception as e:
                print(f"Error sending packet {i}: {e}")

        sock.sendto(b'IMG_END', (UDP_IP, UDP_PORT))  # Indicate end of image
    except Exception as e:
        print(f"Error sending image: {e}")

# Function to handle incoming messages
def receive():
    received_chunks = {}  # Dictionary to store received chunks
    while True:
        try:
            data, addr = sock.recvfrom(65535)  # Buffer size
            sender_ip = addr[0]
            if data.startswith(b'IMG_CHUNK_'):
                # Extract header and chunk data
                header, chunk = data.split(b'\n', 1)
                index, total = map(int, header.decode().split('_')[2:])
                received_chunks[index] = chunk
                
                if len(received_chunks) == total:
                    # Reassemble image
                    complete_image_data = b''.join(received_chunks[i] for i in range(total))
                    received_chunks.clear()
                    
                    # Convert byte stream back to image and display
                    image = Image.open(io.BytesIO(complete_image_data))
                    image.thumbnail((200, 200))  # Resize for display
                    photo = ImageTk.PhotoImage(image)

                    # Display image in the chat log
                    chat_log.config(state=tk.NORMAL)
                    if sender_ip == LOCAL_IP:
                        chat_log.insert(tk.END, f"{sender_ip}(you):\n")
                        chat_log.image_create(tk.END, image=photo)
                        chat_log.insert(tk.END, '\n')  
                    else:
                        chat_log.insert(tk.END, f"{sender_ip}: \n")
                        chat_log.image_create(tk.END, image=photo)
                        chat_log.insert(tk.END, '\n')  
                    chat_log.config(state=tk.DISABLED)
                    chat_log.yview(tk.END)

                    # Keep a reference to avoid garbage collection
                    chat_log.image = photo

            elif data == b'IMG_END':
                pass  # End of image transmission

            else:
                # Handle text messages with sender IP
                message = data.decode()
                chat_log.config(state=tk.NORMAL)
                if sender_ip == LOCAL_IP:
                    chat_log.insert(tk.END, f"{sender_ip} (you): {message}\n")
                else:
                    chat_log.insert(tk.END, f"{sender_ip}: {message}\n")
                chat_log.config(state=tk.DISABLED)
                chat_log.yview(tk.END)

        except Exception as e:
            print(f"Error receiving data: {e}")

# Setup GUI
root = tk.Tk()
root.title("Chat with Images")

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

chat_log = tk.Text(frame, height=20, width=50, state=tk.DISABLED)
chat_log.pack(side=tk.LEFT)

scrollbar = tk.Scrollbar(frame, command=chat_log.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
chat_log.config(yscrollcommand=scrollbar.set)

# Frame for entry and buttons
input_frame = tk.Frame(root)
input_frame.pack(pady=5, padx=10)

entry = tk.Entry(input_frame, width=50)
entry.pack(side=tk.LEFT)

send_button = tk.Button(input_frame, text="Send", command=send_message)
send_button.pack(side=tk.LEFT, padx=5)

send_image_button = tk.Button(input_frame, text="Send Image", command=send_image)
send_image_button.pack(side=tk.LEFT, padx=5)

# Bind Enter key to send_message function
root.bind('<Return>', send_message)

# Setup UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('', UDP_PORT))

# Start receiving thread
recv_thread = threading.Thread(target=receive, daemon=True)
recv_thread.start()

# Start GUI event loop
root.mainloop()

# Close socket when exiting
sock.close()
