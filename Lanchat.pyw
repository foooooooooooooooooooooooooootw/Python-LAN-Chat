import tkinter as tk
from tkinter import filedialog
import socket
from PIL import Image, ImageTk
import io
import threading
import os
import time

# Configuration
UDP_IP = '192.168.1.255'  # Broadcast address, adjust as needed
UDP_PORT = 12345
CHUNK_SIZE = 64000  # Safe size for chunks

# Get local IP address
LOCAL_IP = socket.gethostbyname(socket.gethostname())

# List to store references to PhotoImage objects
image_references = []

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

# Function to resize image if necessary
def resize_image_if_necessary(image):
    width, height = image.size
    max_dimension = 400
    if width > max_dimension or height > max_dimension:
        if width > height:
            new_width = max_dimension
            new_height = int((max_dimension / width) * height)
        else:
            new_height = max_dimension
            new_width = int((max_dimension / height) * width)
        image = image.resize((new_width, new_height), Image.LANCZOS)
    return image

# Function to send image over UDP
def send_image_over_udp(image_path):
    try:
        # Open image and resize if necessary
        image = Image.open(image_path)
        image = resize_image_if_necessary(image)

        # Convert image to byte stream
        with io.BytesIO() as byte_stream:
            image.save(byte_stream, format='PNG')
            byte_data = byte_stream.getvalue()

        # Extract the file name from the path
        file_name = os.path.basename(image_path)

        # Send the file name first
        header = f'IMG_FILE_NAME_{file_name}'.encode()
        sock.sendto(header, (UDP_IP, UDP_PORT))

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
                print(f"Sent chunk {i+1}/{total_chunks}, size: {len(packet)} bytes")
            except Exception as e:
                print(f"Error sending packet {i}: {e}")

        sock.sendto(b'IMG_END', (UDP_IP, UDP_PORT))  # Indicate end of image
    except Exception as e:
        print(f"Error sending image: {e}")

# Function to handle incoming messages
def receive():
    received_chunks = {}  # Dictionary to store received chunks
    file_name = None  # Variable to store the file name
    while True:
        try:
            data, addr = sock.recvfrom(65535)  # Buffer size
            sender_ip = addr[0]
            
            if data.startswith(b'IMG_FILE_NAME_'):
                # Extract and store the file name
                file_name = data.decode().split('IMG_FILE_NAME_')[1]
                print(f"Received file name: {file_name}")

            elif data.startswith(b'IMG_CHUNK_'):
                # Extract header and chunk data
                header, chunk = data.split(b'\n', 1)
                index, total = map(int, header.decode().split('_')[2:])
                received_chunks[index] = chunk

                print(f"Received chunk {index}/{total}")  # Debugging

                if len(received_chunks) == total:
                    # Reassemble image
                    complete_image_data = b''.join(received_chunks[i] for i in range(total))
                    received_chunks.clear()
                    
                    # Convert byte stream back to image and display
                    try:
                        print("Reassembling image...")
                        image = Image.open(io.BytesIO(complete_image_data))
                        image = resize_image_if_necessary(image)  # Resize if necessary
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
                        image_references.append(photo)

                        # Bind click event to save image with the file name
                        chat_log.bind("<Button-1>", lambda e: save_image_on_click(e, complete_image_data, file_name))

                    except Exception as e:
                        print(f"Error displaying image: {e}")

            elif data == b'IMG_END':
                print("Image transmission ended.")  # Debugging

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

# Function to save image when clicked
def save_image_on_click(event, image_data, file_name):
    try:
        # Use the file name received from the sender
        default_filename = file_name if file_name else f"image_{int(time.time())}.png"
        
        # Open save file dialog with default file name
        file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")], initialfile=default_filename)
        if file_path:
            with open(file_path, 'wb') as file:
                file.write(image_data)
            print(f"Image saved as {file_path}")
    except Exception as e:
        print(f"Error saving image: {e}")

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

# Increase socket buffer size
sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65535)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65535)

# Start receiving thread
recv_thread = threading.Thread(target=receive, daemon=True)
recv_thread.start()

# Start GUI event loop
root.mainloop()

# Close socket when exiting
sock.close()
