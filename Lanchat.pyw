#V2.4 18/9/24
#TODO add settings? settings should include colours of windows, text, etc. Maybe even settings on where the files are saved. 
#TODO add video player?

import subprocess
import sys

# Function to check and install missing dependencies
def check_and_install(package):
    try:
        __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

def install_dependencies():
    packages = ['Pillow', 'tkinterdnd2', 'requests']
    for package in packages:
        check_and_install(package)

install_dependencies()

import tkinter as tk
from tkinter import filedialog
from tkinterdnd2 import TkinterDnD, DND_FILES
import socket
from PIL import Image, ImageTk, ImageSequence
import io
import threading
import os
import requests
import time

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
        print(f"Sent message: {message}")  # Debug statement

# Function to open file dialog and send image
def send_image():
    file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.gif;*.WebP;*.TGA;*.TIFF;*.ico")])
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

# Function to send image over UDP (with GIF support)
def send_image_over_udp(image_path):
    try:
        # Check if the file is a GIF based on the file extension
        is_gif = image_path.lower().endswith(".gif")

        # Open the file and read its raw data as bytes
        with open(image_path, 'rb') as file:
            byte_data = file.read()

        file_name = os.path.basename(image_path)
        header = f'GIF_FILE_NAME_{file_name}'.encode() if is_gif else f'IMG_FILE_NAME_{file_name}'.encode()
        sock.sendto(header, (UDP_IP, UDP_PORT))

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

        sock.sendto(b'IMG_END', (UDP_IP, UDP_PORT))

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

def receive():
    received_chunks = {}
    file_name = None
    is_image = False
    is_gif = False
    is_document = False

    while True:
        try:
            data, addr = sock.recvfrom(65535)
            sender_ip = addr[0]

            if data.startswith(b'IMG_FILE_NAME_'):
                file_name = data.decode().split('IMG_FILE_NAME_')[1]
                is_image = True
                is_gif = False
                print(f"Received image file name: {file_name}")

            elif data.startswith(b'GIF_FILE_NAME_'):
                file_name = data.decode().split('GIF_FILE_NAME_')[1]
                is_gif = True
                is_image = False
                print(f"Received GIF file name: {file_name}")

            elif data.startswith(b'IMG_CHUNK_') or data.startswith(b'GIF_CHUNK_'):
                header, chunk = data.split(b'\n', 1)
                index, total = map(int, header.decode().split('_')[2:])
                received_chunks[index] = chunk
                print(f"Received image/GIF chunk {index}/{total}")

                if len(received_chunks) == total:
                    complete_data = b''.join(received_chunks[i] for i in range(total))
                    received_chunks.clear()

                    try:
                        if is_gif:
                            display_gif(None, sender_ip, file_name, complete_data)
                        else:
                            image = Image.open(io.BytesIO(complete_data))
                            display_static_image(image, sender_ip, file_name, complete_data)
                    except Exception as e:
                        print(f"Error displaying image/GIF: {e}")

            elif data.startswith(b'DOC_FILE_NAME_'):
                file_name = data.decode().split('DOC_FILE_NAME_')[1]
                is_document = True
                print(f"Received document file name: {file_name}")

            elif data.startswith(b'DOC_CHUNK_'):
                header, chunk = data.split(b'\n', 1)
                index, total = map(int, header.decode().split('_')[2:])
                received_chunks[index] = chunk

                if len(received_chunks) == total:
                    complete_data = b''.join(received_chunks[i] for i in range(total))
                    received_chunks.clear()

                    # Display a placeholder and metadata for the document
                    display_document_placeholder(file_name, sender_ip, complete_data)

            elif data == b'IMG_END':
                print("Image transmission ended.")

            elif not is_image and not is_gif and not is_document:
                # Handle as text message
                message = data.decode()
                chat_log.config(state=tk.NORMAL)
                if sender_ip == LOCAL_IP:
                    chat_log.insert(tk.END, f"{sender_ip} (you): {message} \n")
                else:
                    chat_log.insert(tk.END, f"{sender_ip}: {message} \n")
                chat_log.config(state=tk.DISABLED)
                chat_log.yview(tk.END)
                print(f"Received message: {message}")

        except Exception as e:
            print(f"Error receiving data: {e}")

def display_document_placeholder(file_name, sender_ip, complete_doc_data):
    try:
        # Load and resize the placeholder image
        placeholder_image_path = os.path.join(APP_DATA_PATH, 'doc.png')
        placeholder_image = Image.open(placeholder_image_path)
        placeholder_image = placeholder_image.resize((133, 200), Image.LANCZOS)
        photo = ImageTk.PhotoImage(placeholder_image)

        # Display the placeholder image in the chat log
        chat_log.config(state=tk.NORMAL)
        if sender_ip == LOCAL_IP:
            chat_log.insert(tk.END, f"{sender_ip} (you):\n")
        else:
            chat_log.insert(tk.END, f"{sender_ip}: \n")

        # Add a Label for the placeholder image
        img_label = tk.Label(chat_log, image=photo, bg=chat_log.cget('bg'), bd=0, highlightthickness=0)
        chat_log.window_create(tk.END, window=img_label)
        chat_log.insert(tk.END, '\n')

        # Add gray text metadata below the image
        file_size_kb = len(complete_doc_data) / 1024  # Calculate file size in KB
        metadata_text = f"{file_name} - {file_size_kb:.2f} KB"
        chat_log.insert(tk.END, metadata_text + "\n", "gray")
        chat_log.tag_configure("gray", foreground="gray")

        chat_log.config(state=tk.DISABLED)
        chat_log.yview(tk.END)
        auto_scroll_chat_log()

        # Keep a reference to avoid garbage collection
        image_references.append(photo)

        # Bind the click event to the image label
        img_label.bind("<Button-1>", lambda e, data=complete_doc_data, name=file_name: save_document_on_click(e, data, name))

    except Exception as e:
        print(f"Error displaying document placeholder: {e}")

def display_static_image(image, sender_ip, file_name, original_image_data):
    try:
        # Resize the image if necessary for display
        resized_image = resize_image_if_necessary(image)

        # Convert the resized image to a PhotoImage object for display
        photo = ImageTk.PhotoImage(resized_image)

        # Extract original resolution and file size
        original_width, original_height = image.size
        file_size_kb = len(original_image_data) / 1024  # File size in KB

        # Insert a label into the chat log where the image will be displayed
        chat_log.config(state=tk.NORMAL)
        if sender_ip == LOCAL_IP:
            chat_log.insert(tk.END, f"{sender_ip} (you):\n")
        else:
            chat_log.insert(tk.END, f"{sender_ip}: \n")

        img_label = tk.Label(chat_log, image=photo)
        chat_log.window_create(tk.END, window=img_label)
        chat_log.insert(tk.END, '\n')

        # Add a gray text label for file metadata below the image
        metadata_text = f"{file_name} - {file_size_kb:.2f} KB - {original_width}x{original_height} pixels"
        chat_log.insert(tk.END, metadata_text + "\n", "gray")

        # Define the style for gray-colored text
        chat_log.tag_configure("gray", foreground="gray")

        chat_log.config(state=tk.DISABLED)
        chat_log.yview(tk.END)
        auto_scroll_chat_log()

        # Keep a reference to avoid garbage collection
        image_references.append(photo)

        # Add a click event to save the original image when clicked
        def save_image(event):
            _, file_extension = os.path.splitext(file_name)
            file_extension = file_extension.lower()

            # Set default extension and file types based on the original image format
            if file_extension in ['.jpg', '.jpeg']:
                filetypes = [("JPEG files", "*.jpg;*.jpeg"), ("All files", "*.*")]
            elif file_extension == '.png':
                filetypes = [("PNG files", "*.png"), ("All files", "*.*")]
            elif file_extension == '.gif':
                filetypes = [("GIF files", "*.gif"), ("All files", "*.*")]
            else:
                filetypes = [(f"{file_extension.upper()} files", f"*{file_extension}"), ("All files", "*.*")]

            # Open the save file dialog with the correct default extension
            file_path = filedialog.asksaveasfilename(defaultextension=file_extension, filetypes=filetypes, initialfile=file_name)
            if file_path:
                try:
                    # Save the original image data to the selected file path
                    with open(file_path, 'wb') as f:
                        f.write(original_image_data)
                    print(f"Image saved as {file_path}")
                except Exception as e:
                    print(f"Error saving image: {e}")

        # Bind the click event to the label
        img_label.bind("<Button-1>", save_image)

    except Exception as e:
        print(f"Error displaying static image: {e}")

def display_gif(gif_image, sender_ip, file_name, original_gif_data, max_display_size=400):
    display_frames = []

    # Open the GIF image from the original GIF data
    gif_image = Image.open(io.BytesIO(original_gif_data))

    # Extract original resolution and file size
    original_width, original_height = gif_image.size
    file_size_kb = len(original_gif_data) / 1024  # File size in KB

    # Resize the GIF frames only for display purposes
    for frame in ImageSequence.Iterator(gif_image):
        frame = frame.copy()

        # Resize each frame to fit within the max display size (e.g., 400x400)
        width, height = frame.size
        if width > max_display_size or height > max_display_size:
            if width > height:
                new_width = max_display_size
                new_height = int((max_display_size / width) * height)
            else:
                new_height = max_display_size
                new_width = int((max_display_size / height) * width)

            frame = frame.resize((new_width, new_height), Image.LANCZOS)

        display_frames.append(frame)

    if not display_frames:
        print("No frames extracted from the GIF.")
        return

    def update_frame(index, img_label):
        if index >= len(display_frames):
            index = 0

        frame = ImageTk.PhotoImage(display_frames[index])
        img_label.config(image=frame)
        img_label.image = frame  # Keep a reference to avoid garbage collection

        delay = gif_image.info.get('duration', 100)
        root.after(delay, update_frame, index + 1, img_label)

    # Display the GIF in the chat log
    chat_log.config(state=tk.NORMAL)
    if sender_ip == LOCAL_IP:
        chat_log.insert(tk.END, f"{sender_ip} (you):\n")
    else:
        chat_log.insert(tk.END, f"{sender_ip}: \n")

    # Create a label to display the GIF
    img_label = tk.Label(chat_log)
    chat_log.window_create(tk.END, window=img_label)
    chat_log.insert(tk.END, '\n')

    # Add gray text metadata below the GIF
    metadata_text = f"{file_name} - {file_size_kb:.2f} KB - {original_width}x{original_height} pixels"
    chat_log.insert(tk.END, metadata_text + "\n", "gray")

    # Define the style for gray-colored text
    chat_log.tag_configure("gray", foreground="gray")

    chat_log.config(state=tk.DISABLED)
    chat_log.yview(tk.END)

    # Start the animation
    update_frame(0, img_label)

    auto_scroll_chat_log()

    # Save the original GIF data when the image is clicked
    def save_gif(event):
        file_path = filedialog.asksaveasfilename(defaultextension=".gif", filetypes=[("GIF files", "*.gif"), ("All files", "*.*")], initialfile=file_name)
        if file_path:
            try:
                # Write the original GIF data directly to the file
                with open(file_path, 'wb') as f:
                    f.write(original_gif_data)
                print(f"Original GIF size: {len(original_gif_data)} bytes")
                print(f"GIF saved as {file_path}")
            except Exception as e:
                print(f"Error saving GIF: {e}")

    # Bind the save function to the click event
    img_label.bind("<Button-1>", save_gif)

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
        # Extract file extension from the file name
        _, file_extension = os.path.splitext(file_name)
        file_extension = file_extension.lower()
        
        # Set default file type and extension for the save file dialog
        if not file_extension:  # Default to .pdf if no extension
            file_extension = ".pdf"

        # Define file types for the save dialog
        filetypes = [(f"{file_extension[1:].upper()} files", f"*{file_extension}"), ("All files", "*.*")]
        
        # Open save file dialog with the appropriate default extension
        file_path = filedialog.asksaveasfilename(
            defaultextension=file_extension,
            filetypes=filetypes,
            initialfile=file_name
        )
        
        if file_path:
            # Save the document data to the selected file path
            with open(file_path, 'wb') as f:
                f.write(file_data)
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

# Ensure the chat log auto-scrolls to the newest message after adding any message
def auto_scroll_chat_log():
    chat_log.yview_moveto(1.0)  # Move scrollbar to the bottom

# Setup GUI
root = TkinterDnD.Tk()  # Use TkinterDnD.Tk() instead of tk.Tk()
root.title("Python LAN Chat")

root.iconbitmap(ICON_PATH)

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

chat_log = tk.Text(frame, height=30, width=90, state=tk.DISABLED)
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
