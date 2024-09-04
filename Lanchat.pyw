import tkinter as tk
from tkinter import filedialog
from tkinterdnd2 import TkinterDnD, DND_FILES
import socket
from PIL import Image, ImageTk
import io
import threading
import os
import requests
import time
import subprocess
import sys

# Function to check and install missing dependencies
def check_and_install(package):
    try:
        __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

def install_dependencies():
    packages = ['Pillow', 'tkinterdnd2']
    for package in packages:
        check_and_install(package)

install_dependencies()

# Configuration
UDP_IP = '192.168.1.255'  # Broadcast address, adjust as needed
UDP_PORT = 12345
CHUNK_SIZE = 64000  # Safe size for chunks

# Get local IP address
LOCAL_IP = socket.gethostbyname(socket.gethostname())

# List to store references to PhotoImage objects
image_references = []

# Placeholder image URL and local storage paths
PLACEHOLDER_IMAGE_URL = 'https://raw.githubusercontent.com/foooooooooooooooooooooooooootw/Python-LAN-Chat/main/doc.png'
APP_DATA_PATH = os.path.join(os.getenv('APPDATA', ''), 'PythonLANChat') if os.name == 'nt' else os.path.expanduser('~/.PythonLANChat')

ICON_URL = 'https://raw.githubusercontent.com/foooooooooooooooooooooooooootw/Python-LAN-Chat/main/pythonlanchat.ico'

# Ensure the local folder exists
os.makedirs(APP_DATA_PATH, exist_ok=True)

PLACEHOLDER_IMAGE_PATH = os.path.join(APP_DATA_PATH, 'doc.png')
ICON_PATH = os.path.join(APP_DATA_PATH, 'pythonlanchat.ico')

# Download the placeholder image if not already downloaded
def download_placeholder_image():
    if not os.path.exists(PLACEHOLDER_IMAGE_PATH):
        try:
            response = requests.get(PLACEHOLDER_IMAGE_URL)
            response.raise_for_status()
            with open(PLACEHOLDER_IMAGE_PATH, 'wb') as f:
                f.write(response.content)
            print("Placeholder image downloaded.")
        except Exception as e:
            print(f"Error downloading placeholder image: {e}")

download_placeholder_image()

def download_icon():
    if not os.path.exists(ICON_PATH):
        try:
            response = requests.get(ICON_URL)
            response.raise_for_status()
            with open(ICON_PATH, 'wb') as f:
                f.write(response.content)
            print("Icon downloaded.")
        except Exception as e:
            print(f"Error downloading Icon: {e}")

download_icon()

# Function to send text messages
def send_message(event=None):
    message = entry.get()
    if message:
        sock.sendto(message.encode(), (UDP_IP, UDP_PORT))
        entry.delete(0, tk.END)

# Function to open file dialog and send image
def send_image():
    file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.WebP;*.TGA;*.TIFF;*.ico")])
    if file_path:
        send_image_over_udp(file_path)

# Function to open file dialog and send documents
def send_document():
    file_path = filedialog.askopenfilename(filetypes=[("All files", "*.*")])
    if file_path:
        send_document_over_udp(file_path)

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

# Function to send document over UDP
def send_document_over_udp(file_path):
    try:
        # Read document file
        with open(file_path, 'rb') as file:
            file_data = file.read()

        # Extract the file name from the path
        file_name = os.path.basename(file_path)

        # Send the file name first
        header = f'DOC_FILE_NAME_{file_name}'.encode()
        sock.sendto(header, (UDP_IP, UDP_PORT))

        # Send the placeholder image
        placeholder_image = Image.open(PLACEHOLDER_IMAGE_PATH)
        placeholder_image = placeholder_image.resize((133, 200), Image.LANCZOS)
        with io.BytesIO() as byte_stream:
            placeholder_image.save(byte_stream, format='PNG')
            placeholder_data = byte_stream.getvalue()

        # Send the placeholder image
        placeholder_header = f'DOC_PLACEHOLDER_{file_name}'.encode()
        sock.sendto(placeholder_header, (UDP_IP, UDP_PORT))

        # Split file_data into chunks
        total_chunks = (len(file_data) + CHUNK_SIZE - 1) // CHUNK_SIZE
        for i in range(total_chunks):
            start = i * CHUNK_SIZE
            end = start + CHUNK_SIZE
            chunk = file_data[start:end]
            chunk_header = f'DOC_CHUNK_{i}_{total_chunks}'.encode()
            packet = chunk_header + b'\n' + chunk
            try:
                sock.sendto(packet, (UDP_IP, UDP_PORT))
                print(f"Sent chunk {i+1}/{total_chunks}, size: {len(packet)} bytes")
            except Exception as e:
                print(f"Error sending packet {i}: {e}")

        sock.sendto(b'DOC_END', (UDP_IP, UDP_PORT))  # Indicate end of document
    except Exception as e:
        print(f"Error sending document: {e}")

# Function to handle incoming messages
def receive():
    received_chunks = {}  # Dictionary to store received chunks
    file_name = None  # Variable to store the file name
    is_image = False
    is_document = False
    is_placeholder = False

    while True:
        try:
            data, addr = sock.recvfrom(65535)  # Buffer size
            sender_ip = addr[0]

            if data.startswith(b'IMG_FILE_NAME_'):
                # Extract and store the file name
                file_name = data.decode().split('IMG_FILE_NAME_')[1]
                is_image = True
                print(f"Received image file name: {file_name}")

            elif data.startswith(b'DOC_FILE_NAME_'):
                # Extract and store the file name
                file_name = data.decode().split('DOC_FILE_NAME_')[1]
                is_document = True
                print(f"Received document file name: {file_name}")

            elif data.startswith(b'DOC_PLACEHOLDER_'):
                # Handle the placeholder image for documents
                file_name = data.decode().split('DOC_PLACEHOLDER_')[1]
                is_placeholder = True
                print(f"Received placeholder for document: {file_name}")

            elif data.startswith(b'IMG_CHUNK_'):
                # Extract header and chunk data
                header, chunk = data.split(b'\n', 1)
                index, total = map(int, header.decode().split('_')[2:])
                received_chunks[index] = chunk

                print(f"Received image chunk {index}/{total}")  # Debugging

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
                            chat_log.insert(tk.END, f"{sender_ip} (you):\n")
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

            elif data.startswith(b'DOC_CHUNK_'):
                # Extract header and chunk data
                header, chunk = data.split(b'\n', 1)
                index, total = map(int, header.decode().split('_')[2:])
                received_chunks[index] = chunk

                print(f"Received document chunk {index}/{total}")  # Debugging

                if len(received_chunks) == total:
                    # Reassemble document
                    complete_doc_data = b''.join(received_chunks[i] for i in range(total))
                    received_chunks.clear()

                    # Display placeholder image
                    try:
                        placeholder_image = Image.open(PLACEHOLDER_IMAGE_PATH)
                        placeholder_image = placeholder_image.resize((133, 200), Image.LANCZOS)
                        photo = ImageTk.PhotoImage(placeholder_image)

                        # Display placeholder in the chat log
                        chat_log.config(state=tk.NORMAL)
                        if sender_ip == LOCAL_IP:
                            chat_log.insert(tk.END, f"{sender_ip} (you):\n")
                            chat_log.insert(tk.END, f"{file_name}\n")
                            chat_log.image_create(tk.END, image=photo)
                            chat_log.insert(tk.END, '\n')  
                        else:
                            chat_log.insert(tk.END, f"{sender_ip}: \n")
                            chat_log.insert(tk.END, f"{file_name}\n")
                            chat_log.image_create(tk.END, image=photo)
                            chat_log.insert(tk.END, '\n')  
                        chat_log.config(state=tk.DISABLED)
                        chat_log.yview(tk.END)

                        # Keep a reference to avoid garbage collection
                        image_references.append(photo)

                        # Bind click event to save document with the file name
                        chat_log.bind("<Button-1>", lambda e: save_document_on_click(e, complete_doc_data, file_name))

                    except Exception as e:
                        print(f"Error displaying placeholder: {e}")

            elif data == b'IMG_END':
                print("Image transmission ended.")  # Debugging

            elif data == b'DOC_END':
                print("Document transmission ended.")  # Debugging

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
        _, file_extension = os.path.splitext(file_name)
        default_extension = file_extension if file_extension else ".png"
        default_filename = file_name if file_name else f"image_{int(time.time())}.png"
        
        # Open save file dialog with default file name
        file_path = filedialog.asksaveasfilename(defaultextension=default_extension, filetypes=[("All files", "*.*")], initialfile=default_filename)
        if file_path:
            with open(file_path, 'wb') as file:
                file.write(image_data)
            print(f"Image saved as {file_path}")
    except Exception as e:
        print(f"Error saving image: {e}")

# Function to save document when clicked
def save_document_on_click(event, file_data, file_name):
    try:
        # Extract file extension from file name
        _, file_extension = os.path.splitext(file_name)
        default_extension = file_extension if file_extension else ".pdf"
        
        # Open save file dialog with default file name
        file_path = filedialog.asksaveasfilename(defaultextension=default_extension, filetypes=[("All files", "*.*")], initialfile=file_name)
        if file_path:
            with open(file_path, 'wb') as file:
                file.write(file_data)
            print(f"Document saved as {file_path}")
    except Exception as e:
        print(f"Error saving document: {e}")

# Function to handle file drop
def on_drop(event):
    files = root.tk.splitlist(event.data)
    for file in files:
        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.tga', '.tiff', '.ico')):
            send_image_over_udp(file)
        else:
            send_document_over_udp(file)

# Setup GUI
root = TkinterDnD.Tk()  # Use TkinterDnD.Tk() instead of tk.Tk()
root.title("Python LAN Chat")

root.iconbitmap(ICON_PATH)

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

chat_log = tk.Text(frame, height=20, width=65, state=tk.DISABLED)
chat_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

scrollbar = tk.Scrollbar(frame, command=chat_log.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
chat_log.config(yscrollcommand=scrollbar.set)

input_frame = tk.Frame(root)
input_frame.pack(pady=5, padx=10, fill=tk.X)

entry = tk.Entry(input_frame, width=50)
entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

send_button = tk.Button(input_frame, text=">>>", command=send_message)
send_button.pack(side=tk.LEFT, padx=5)

send_image_button = tk.Button(input_frame, text="Send Image", command=send_image)
send_image_button.pack(side=tk.LEFT, padx=5)

send_document_button = tk.Button(input_frame, text="Send Document", command=send_document)
send_document_button.pack(side=tk.LEFT, padx=5)

root.bind('<Return>', send_message)

# Enable drag-and-drop for the chat_log widget
chat_log.drop_target_register(DND_FILES)
chat_log.dnd_bind('<<Drop>>', on_drop)

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
