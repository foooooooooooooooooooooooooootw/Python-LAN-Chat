#V2.3 18/9/24
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
    is_gif = False
    is_document = False

    while True:
        try:
            data, addr = sock.recvfrom(65535)  # Buffer size
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
                # Handle image or GIF chunks the same way
                header, chunk = data.split(b'\n', 1)
                index, total = map(int, header.decode().split('_')[2:])
                received_chunks[index] = chunk

                print(f"Received image/GIF chunk {index}/{total}")

                if len(received_chunks) == total:
                    # Reassemble the complete image or GIF data
                    complete_data = b''.join(received_chunks[i] for i in range(total))
                    received_chunks.clear()

                    try:
                        if is_gif:
                            # Do not process the original GIF; just display it and pass the original data
                            display_gif(None, sender_ip, file_name, complete_data)  # Passing original GIF data
                        else:
                            # Process and display static images
                            image = Image.open(io.BytesIO(complete_data))
                            display_static_image(image, sender_ip, file_name, complete_data)  # Pass original image data
                    except Exception as e:
                        print(f"Error displaying image/GIF: {e}")

            elif data == b'IMG_END':
                print("Image transmission ended.")

        except Exception as e:
            print(f"Error receiving data: {e}")



def display_document_placeholder(file_name, sender_ip, complete_doc_data):
    try:
        # Open and resize the placeholder image
        placeholder_image = Image.open(PLACEHOLDER_IMAGE_PATH)
        placeholder_image = placeholder_image.resize((133, 200), Image.LANCZOS)
        photo = ImageTk.PhotoImage(placeholder_image)

        # Display placeholder in the chat log
        chat_log.config(state=tk.NORMAL)
        if sender_ip == LOCAL_IP:
            chat_log.insert(tk.END, f"{sender_ip} (you):\n")
            chat_log.insert(tk.END, f"{file_name}\n")
            auto_scroll_chat_log()   
        else:
            chat_log.insert(tk.END, f"{sender_ip}: \n")
            chat_log.insert(tk.END, f"{file_name}\n")
            auto_scroll_chat_log()   

        # Assign a unique tag for the placeholder
        tag_name = f"doc_{len(image_references)}"
        chat_log.image_create(tk.END, image=photo)
        chat_log.insert(tk.END, '\n')
        auto_scroll_chat_log()   
        chat_log.tag_add(tag_name, f"end-2c linestart", f"end-2c lineend")

        chat_log.config(state=tk.DISABLED)
        chat_log.yview(tk.END)

        # Keep a reference to avoid garbage collection
        image_references.append(photo)

        # Bind click event to save the specific document with the file name
        chat_log.tag_bind(tag_name, "<Button-1>", lambda e, data=complete_doc_data, name=file_name: save_document_on_click(e, data, name))

    except Exception as e:
        print(f"Error displaying document placeholder: {e}")

def display_static_image(image, sender_ip, file_name, original_image_data):
    try:
        # Resize the image if necessary for display
        resized_image = resize_image_if_necessary(image)

        # Convert the resized image to a PhotoImage object for display
        photo = ImageTk.PhotoImage(resized_image)

        # Insert a label into the chat log where the image will be displayed
        chat_log.config(state=tk.NORMAL)
        if sender_ip == LOCAL_IP:
            chat_log.insert(tk.END, f"{sender_ip} (you):\n")
        else:
            chat_log.insert(tk.END, f"{sender_ip}: \n")

        img_label = tk.Label(chat_log, image=photo)
        chat_log.window_create(tk.END, window=img_label)
        chat_log.insert(tk.END, '\n')
        chat_log.config(state=tk.DISABLED)
        chat_log.yview(tk.END)

        # Keep a reference to avoid garbage collection
        image_references.append(photo)

        # Add a click event to save the original image when clicked
        def save_image(event):
            # Get the file extension (e.g., ".jpg", ".png") from the file_name
            _, file_extension = os.path.splitext(file_name)
            file_extension = file_extension.lower()  # Normalize extension to lowercase

            # Set default extension and file types based on the original image format
            if file_extension in ['.jpg', '.jpeg']:
                filetypes = [("JPEG files", "*.jpg;*.jpeg"), ("All files", "*.*")]
            elif file_extension == '.png':
                filetypes = [("PNG files", "*.png"), ("All files", "*.*")]
            elif file_extension == '.gif':
                filetypes = [("GIF files", "*.gif"), ("All files", "*.*")]
            else:
                # Fallback for any other extension
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

    # If gif_image is not passed (None), then we are dealing with the original raw GIF data
    if gif_image is None:
        # Use the original GIF data directly for display
        gif_image = Image.open(io.BytesIO(original_gif_data))

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

        # Use the duration from the GIF metadata to control frame timing
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
    chat_log.config(state=tk.DISABLED)
    chat_log.yview(tk.END)

    # Start the animation
    update_frame(0, img_label)

    # Save the original GIF data when the image is clicked
    def save_gif(event):
        file_path = filedialog.asksaveasfilename(defaultextension=".gif", filetypes=[("GIF files", "*.gif"), ("All files", "*.*")], initialfile=file_name)
        if file_path:
            try:
                # Write the original GIF data directly to the file
                with open(file_path, 'wb') as f:
                    f.write(original_gif_data)  # Save the original unmodified GIF
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
