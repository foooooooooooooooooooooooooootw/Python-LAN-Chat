#V2.10 29/9/24
#Add upload progress bar, ability to cancel uploads and prevent main thread from getting blocked by uploads 
#TODO fix not being able to receive messages while uploading
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
from tkinter import ttk
from tkinter import filedialog, colorchooser, simpledialog
from tkinterdnd2 import TkinterDnD, DND_FILES
import socket
from PIL import Image, ImageTk, ImageSequence, ImageDraw, ImageFont, ImageChops
import io
import threading
import os
import requests
import time
import struct
import queue

# Create a queue for safely passing data between threads
message_queue = queue.Queue()
settings_window = None

def create_gear_icon():
    """Create the gear icon (⚙️) dynamically if it doesn't already exist."""
    if not os.path.exists(GEAR_ICON_PATH):
        print("Creating the gear icon for the first time...")
        
        # Define the size of the icon (64x64 is standard for icons)
        size = (256,256)
        
        # Create a new image with a transparent background
        img = Image.new('RGBA', size, (255, 255, 255, 0))
        mask = Image.new('L', size, 0)

        # Create a drawing context
        draw = ImageDraw.Draw(img)
        mask_draw = ImageDraw.Draw(mask)

        # Load a system font that supports emoji rendering (update the font path as needed)
        font_path = "seguiemj.ttf"  # Path to a font that supports emojis. Modify this based on your OS.
        font_size = 192  # Adjust font size to fit inside the icon
        font = ImageFont.truetype(font_path, font_size)

        # Measure the size of the gear emoji
        text = "⚙️"
        # Get the bounding box of the text (x0, y0, x1, y1)
        text_bbox = draw.textbbox((0, 0), text, font=font)

        # Calculate the width and height of the text based on the bounding box
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        # Calculate the position to center the gear emoji within the image
        position_x = (size[0] - text_width) // 2
        position_y = (size[1] - text_height) // 2 + 28

        # Ensure the emoji stays within the bounds (avoid going off-canvas)
        position_x = max(0, position_x)
        position_y = max(0, position_y)

        # Draw the gear emoji centered in the image
        draw.text((position_x, position_y), text, font=font, fill=(0, 0, 0, 255))  # Black color for the emoji

        outline_color = (0, 0, 0, 255)  # Black outline
        for offset in [-2, 0, 2]:  # Adjust outline thickness here
            draw.text((position_x + offset, position_y + offset), text, font=font, fill=outline_color)

        # Create the mask for the gray fill
        mask_draw.text((position_x, position_y), text, font=font, fill=255)  # White on mask

        # Fill the inside of the gear with gray
        fill_color = (169, 169, 169, 255)  # Gray color
        filled_img = Image.new('RGBA', size, fill_color)
        img_with_fill = ImageChops.composite(filled_img, img, mask)  # Apply the mask to fill the inside

        # Save the image as an .ico file
        img_with_fill.save(GEAR_ICON_PATH, format='ICO')
        print(f"Gear icon created at {GEAR_ICON_PATH}")
    else:
        print(f"Gear icon already exists at {GEAR_ICON_PATH}")

# Function to calculate broadcast address based on IP and subnet mask
def get_broadcast_address(ip, subnet_mask):
    ip_bin = struct.unpack('>I', socket.inet_aton(ip))[0]
    mask_bin = struct.unpack('>I', socket.inet_aton(subnet_mask))[0]
    broadcast_bin = ip_bin | ~mask_bin
    broadcast_ip = socket.inet_ntoa(struct.pack('>I', broadcast_bin & 0xFFFFFFFF))
    return broadcast_ip

# Function to get the subnet mask on Windows using ipconfig
def get_subnet_mask_windows(interface_name):
    try:
        output = subprocess.check_output("ipconfig").decode('utf-8')
        for line in output.splitlines():
            if interface_name in line:
                for next_line in output.splitlines():
                    if "Subnet Mask" in next_line:
                        return next_line.split(":")[-1].strip()
    except Exception as e:
        print(f"Error retrieving subnet mask on Windows: {e}")
    return None

# Function to get the subnet mask on Linux/macOS using fcntl
def get_subnet_mask_unix(ifname):
    import fcntl
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(
            sock.fileno(),
            0x891b,  # SIOCGIFNETMASK for Linux/macOS
            struct.pack('256s', ifname[:15].encode('utf-8'))
        )[20:24])
    except Exception as e:
        print(f"Error getting subnet mask on Unix: {e}")
        return None

# Function to get local IP address (different methods for Windows and Unix)
def get_local_ip(ifname):
    if os.name == 'nt':  # Windows
        try:
            output = subprocess.check_output("ipconfig").decode('utf-8')
            for line in output.splitlines():
                if ifname in line:
                    for next_line in output.splitlines():
                        if "IPv4 Address" in next_line:
                            return next_line.split(":")[-1].strip()
        except Exception as e:
            print(f"Error retrieving local IP on Windows: {e}")
    else:  # Unix-like systems
        try:
            import fcntl
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            return socket.inet_ntoa(fcntl.ioctl(
                sock.fileno(),
                0x8915,  # SIOCGIFADDR for Linux/macOS
                struct.pack('256s', ifname[:15].encode('utf-8'))
            )[20:24])
        except Exception as e:
            print(f"Error retrieving local IP on Unix: {e}")
    return None

# Function to detect the active interface (Windows or Unix)
def get_active_interface():
    try:
        if os.name == 'posix':  # Unix-like systems
            if sys.platform == 'linux' or sys.platform == 'darwin':  # Linux or macOS
                if os.path.exists('/sys/class/net/eth0'):
                    return 'eth0'
                elif os.path.exists('/sys/class/net/wlan0'):
                    return 'wlan0'
                else:
                    raise Exception("No active ethernet or wifi interfaces found.")
        elif os.name == 'nt':  # Windows
            interfaces = subprocess.check_output("ipconfig").decode('utf-8')
            if 'Ethernet adapter' in interfaces:
                return 'Ethernet'
            elif 'Wireless LAN adapter' in interfaces:
                return 'Wi-Fi'
            else:
                raise Exception("No active ethernet or wifi interfaces found.")
    except Exception as e:
        print(f"Error detecting active interface: {e}")
        return None

# Main logic to detect broadcast address
def detect_broadcast_address():
    active_interface = get_active_interface()
    if not active_interface:
        return None

    local_ip = get_local_ip(active_interface)
    if not local_ip:
        return None

    if os.name == 'nt':  # Windows
        subnet_mask = get_subnet_mask_windows(active_interface)
    else:  # Unix-like systems
        subnet_mask = get_subnet_mask_unix(active_interface)

    if not subnet_mask:
        return None

    broadcast_address = get_broadcast_address(local_ip, subnet_mask)
    return broadcast_address

# Example usage:
broadcast_address = detect_broadcast_address()
if broadcast_address:
    print(f"Detected broadcast address: {broadcast_address}")
else:
    print("Failed to detect broadcast address.")

sent_message_color = "#CE123E"  # Default color for sent messages
received_message_color = "#167F8D"  # Default color for received messages

# Function to open the settings window
def open_settings():
    global sent_message_color, received_message_color, settings_window
    
    if settings_window is None or not settings_window.winfo_exists():
    # Create a new top-level window for settings
        settings_window = tk.Toplevel(root)
        settings_window.title("Settings")
        settings_window.geometry("300x350")  # Set window size for better layout

        # Background color option
        def change_bg_color():
            color = colorchooser.askcolor()[1]
            if color:
                chat_log.config(bg=color)

            # Font color option for sent messages
        def change_sent_message_color():
            global sent_message_color
            color = colorchooser.askcolor()[1]
            if color:
                sent_message_color = color

        # Font color option for received messages
        def change_received_message_color():
            global received_message_color
            color = colorchooser.askcolor()[1]
            if color:
                received_message_color = color

        # Function to safely switch to a new port by re-binding the socket
        def switch_port(preset_port):
            global UDP_PORT, sock
            try:
                UDP_PORT = preset_port
                sock.close()  # Close the existing socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Create a new socket
                sock.bind(('', UDP_PORT))  # Rebind to the new port
                tk.messagebox.showinfo("Port Changed", f"Port changed to {UDP_PORT}")
            except Exception as e:
                tk.messagebox.showerror("Port Error", f"Failed to bind to port {UDP_PORT}. Error: {e}")

        # Function to enter a custom port
        def change_custom_port():
            global UDP_PORT, sock
            try:
                new_port = simpledialog.askinteger("Port Settings", "Enter custom Send Port:", initialvalue=UDP_PORT)
                if new_port:
                    UDP_PORT = new_port
                    sock.close()  # Close the existing socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Create a new socket
                    sock.bind(('', UDP_PORT))  # Rebind to the new port
                    tk.messagebox.showinfo("Port Changed", f"Custom port changed to {UDP_PORT}")
            except Exception as e:
                tk.messagebox.showerror("Port Error", f"Failed to bind to custom port {UDP_PORT}. Error: {e}")

        def change_address():
            global UDP_IP
            new_ip = simpledialog.askstring("Address Settings", "Enter new broadcast address (e.g., 192.168.1.255):", initialvalue=UDP_IP)
            if new_ip:
                UDP_IP = new_ip

        # Set the icon for the settings window
        settings_window.iconbitmap(GEAR_ICON_PATH) 

        def on_closing():
                global settings_window
                settings_window.destroy()
                settings_window = None  # Reset the global variable when closed

        settings_window.protocol("WM_DELETE_WINDOW", on_closing)  # Handle window close
        # Beautified layout with sections
        settings_frame = tk.LabelFrame(settings_window, text="Colour Settings", padx=10, pady=10)
        settings_frame.pack(pady=10)

        cs_row_1 = tk.Frame(settings_frame)
        cs_row_1.pack()
        tk.Button(cs_row_1, text="Background Colour", width=24, command=change_bg_color).pack(side=tk.TOP, padx=5, pady=5)

        cs_row_2 = tk.Frame(settings_frame)
        cs_row_2.pack()
        tk.Button(cs_row_2, text="Sent Message Colour", width=24, command=change_sent_message_color).pack(side=tk.TOP, padx=5, pady=5)

        cs_row_3 = tk.Frame(settings_frame)
        cs_row_3.pack()
        tk.Button(cs_row_3, text="Received Message Colour", width=24, command=change_received_message_color).pack(side=tk.TOP, padx=5, pady=5)

        # Port selection section
        port_frame = tk.LabelFrame(settings_window, text="Select Channel (Port)", padx=10, pady=10)
        port_frame.pack(pady=10, padx=10, fill="both")

        pf_row_1 = tk.Frame(port_frame)
        pf_row_1.pack()
        tk.Button(pf_row_1, text="12345", width=8, command=lambda: switch_port(12345)).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(pf_row_1, text="22222", width=8, command=lambda: switch_port(22222)).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(pf_row_1, text="33333", width=8, command=lambda: switch_port(33333)).pack(side=tk.LEFT, padx=5, pady=5)

        pf_row_2 = tk.Frame(port_frame)
        pf_row_2.pack() 
        tk.Button(pf_row_2, text="44444", width=12, command=lambda: switch_port(44444)).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(pf_row_2, text="Custom Channel", width=15, command=change_custom_port).pack(side=tk.LEFT, padx=5, pady=5)

        # Custom channel button
        channel_button = tk.Button(settings_window, text="Change Broadcast Address", command=change_address)
        channel_button.pack(pady=5)
    
    else:
        # If it exists, just raise it to the front
        settings_window.lift()
        settings_window.focus_force()
    
# Use this dynamically detected broadcast address in your configuration
UDP_IP = broadcast_address if broadcast_address else '192.168.1.255'  # Fallback to hardcoded value if detection fails
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
GEAR_ICON_PATH = os.path.join(APP_DATA_PATH, 'gear.ico')
create_gear_icon()

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
cancel_flag = False

def cancel_upload():
    global cancel_flag
    cancel_flag = True  # Set the flag to cancel the upload
    clear_upload_frame()
    chat_log.config(state=tk.NORMAL)
    chat_log.insert(tk.END, "Upload canceled.\n", "gray")
    chat_log.tag_configure("gray", foreground="gray")
    chat_log.config(state=tk.DISABLED)

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

def send_image_over_udp(image_path):
    global cancel_flag
    cancel_flag = False  # Reset the cancel flag

    upload_frame.pack(before=input_frame, fill=tk.X, pady=5)
    for widget in upload_frame.winfo_children():
        widget.destroy()  # Remove any existing widgets

    progress_bar = ttk.Progressbar(upload_frame, length=600, mode='determinate')
    progress_bar.pack(side=tk.LEFT, padx=10)

    progress_label = tk.Label(upload_frame, text="0%")
    progress_label.pack(side=tk.LEFT, padx=10)

    cancel_button = tk.Button(upload_frame, text="Cancel", command=lambda: cancel_upload())
    cancel_button.pack(side=tk.LEFT, padx=10)

    def upload_image():
        try:
            is_gif = image_path.lower().endswith(".gif")
            with open(image_path, 'rb') as file:
                byte_data = file.read()

            file_name = os.path.basename(image_path)
            header = f'GIF_FILE_NAME_{file_name}'.encode() if is_gif else f'IMG_FILE_NAME_{file_name}'.encode()
            sock.sendto(header, (UDP_IP, UDP_PORT))

            total_chunks = (len(byte_data) + CHUNK_SIZE - 1) // CHUNK_SIZE
            for i in range(total_chunks):
                if cancel_flag:  # Check if upload was canceled
                    print("Upload canceled")
                    break

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
                
                # Update progress
                percent_complete = ((i + 1) / total_chunks) * 100
                progress_bar['value'] = percent_complete
                progress_label.config(text=f"{percent_complete:.2f}%")

            sock.sendto(b'IMG_END', (UDP_IP, UDP_PORT))

            upload_frame.pack_forget()

        except Exception as e:
            print(f"Error sending image: {e}")

    # Start the upload in a new thread
    threading.Thread(target=upload_image, daemon=True).start()

def send_document_over_udp(file_path):
    global cancel_flag
    cancel_flag = False  # Reset the cancel flag

    upload_frame.pack(before=input_frame, fill=tk.X, pady=5)
    for widget in upload_frame.winfo_children():
        widget.destroy()  # Remove any existing widgets

    progress_bar = ttk.Progressbar(upload_frame, length=600, mode='determinate')
    progress_bar.pack(side=tk.LEFT, padx=10)

    progress_label = tk.Label(upload_frame, text="0%")
    progress_label.pack(side=tk.LEFT, padx=10)

    cancel_button = tk.Button(upload_frame, text="Cancel", command=lambda: cancel_upload())
    cancel_button.pack(side=tk.LEFT, padx=10)

    def upload_document():
        try:
            with open(file_path, 'rb') as file:
                file_data = file.read()

            file_name = os.path.basename(file_path)
            header = f'DOC_FILE_NAME_{file_name}'.encode()
            sock.sendto(header, (UDP_IP, UDP_PORT))

            total_chunks = (len(file_data) + CHUNK_SIZE - 1) // CHUNK_SIZE
            for i in range(total_chunks):
                if cancel_flag:  # Check if upload was canceled
                    print("Upload canceled")
                    break
                
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
                
                # Update progress
                percent_complete = ((i + 1) / total_chunks) * 100
                progress_bar['value'] = percent_complete
                progress_label.config(text=f"{percent_complete:.2f}%")

            sock.sendto(b'DOC_END', (UDP_IP, UDP_PORT))
            
            upload_frame.pack_forget()

        except Exception as e:
            print(f"Error sending document: {e}")

    # Start the upload in a new thread
    threading.Thread(target=upload_document, daemon=True).start()

CHUNK_TIMEOUT = 2

# Global variables to hold the state of file transfers
received_chunks = {}
file_name = None
is_image = False
is_gif = False
is_document = False
last_received_time = None 

# Function to handle received messages, safely adding them to the queue
def receive():
    global received_chunks, file_name, is_image, is_gif, is_document

    while True:
        try:
            data, addr = sock.recvfrom(65535)  # Receiving data from socket
            sender_ip = addr[0]

            # Add the received data to the queue for processing in the main thread
            message_queue.put((sender_ip, data))

        except Exception as e:
            print(f"Error receiving data: {e}")

def reset_transfer_flags():
    """Helper function to reset the state flags."""
    global is_image, is_gif, is_document, received_chunks, file_name, last_received_time
    is_image = False
    is_gif = False
    is_document = False
    received_chunks.clear()
    file_name = None
    last_received_time = None

# Function to process messages from the queue in the main thread
def process_queue():
    global received_chunks, file_name, is_image, is_gif, is_document, last_received_time

    try:
        while not message_queue.empty():
            sender_ip, data = message_queue.get()

            if data.startswith(b'IMG_FILE_NAME_'):
                file_name = data.decode().split('IMG_FILE_NAME_')[1]
                is_image = True
                is_gif = False
                is_document = False
                last_received_time = time.time()
                print(f"Received image file name: {file_name}")

            elif data.startswith(b'GIF_FILE_NAME_'):
                file_name = data.decode().split('GIF_FILE_NAME_')[1]
                is_gif = True
                is_image = False
                is_document = False
                last_received_time = time.time()
                print(f"Received GIF file name: {file_name}")

            elif data.startswith(b'IMG_CHUNK_') or data.startswith(b'GIF_CHUNK_'):
                header, chunk = data.split(b'\n', 1)
                index, total = map(int, header.decode().split('_')[2:])
                received_chunks[index] = chunk
                last_received_time = time.time()
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

                    finally:
                        # Always reset the state flags after processing
                        reset_transfer_flags()

            elif data.startswith(b'DOC_FILE_NAME_'):
                file_name = data.decode().split('DOC_FILE_NAME_')[1]
                is_document = True
                is_image = False
                is_gif = False
                last_received_time = time.time()
                print(f"Received document file name: {file_name}")

            elif data.startswith(b'DOC_CHUNK_'):
                header, chunk = data.split(b'\n', 1)
                index, total = map(int, header.decode().split('_')[2:])
                received_chunks[index] = chunk
                last_received_time = time.time()

                if len(received_chunks) == total:
                    try:
                        complete_data = b''.join(received_chunks[i] for i in range(total))
                        received_chunks.clear()

                        # Display a placeholder and metadata for the document
                        display_document_placeholder(file_name, sender_ip, complete_data)
                    except Exception as e:
                        print(f"Error displaying document: {e}")
                    finally:
                        # Always reset the state flags after processing
                        reset_transfer_flags()
            
            elif data == b'DOC_END':
                print("Document transmission ended.")
                reset_transfer_flags() 
                continue

            elif data == b'IMG_END':
                print("Image transmission ended.")
                reset_transfer_flags()

            elif not is_image and not is_gif and not is_document:
                # Handle as text message
                message = data.decode()
                display_message(sender_ip, message)
                print(f"Received message: {message}")
        
        if last_received_time and time.time() - last_received_time > CHUNK_TIMEOUT:
            print(f"Timeout reached: discarding incomplete transfer for {file_name}")
            reset_transfer_flags()

        # Schedule the next call to process_queue
        root.after(100, process_queue)

    except Exception as e:
        print(f"Error processing queue: {e}")

# Function to display text messages with proper tagging
def display_message(sender_ip, message):
    chat_log.config(state=tk.NORMAL)  # Enable editing
    if sender_ip == LOCAL_IP:
        chat_log.insert(tk.END, f"{sender_ip} (you): {message}\n", ("sent_message",))
    else:
        chat_log.insert(tk.END, f"{sender_ip}: {message}\n", ("received_message",))
    chat_log.config(state=tk.DISABLED)  # Disable editing after inserting
    chat_log.yview(tk.END)  # Scroll to the end

# Function to display document placeholder
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
            chat_log.insert(tk.END, f"{sender_ip} (you):\n", "sent_message")
        else:
            chat_log.insert(tk.END, f"{sender_ip}: \n", "received_message")

        # Add a Label for the placeholder image
        img_label = tk.Label(chat_log, image=photo, bg=chat_log.cget('bg'), bd=0, highlightthickness=0)
        chat_log.window_create(tk.END, window=img_label)
        chat_log.insert(tk.END, '\n')

        # Add gray text metadata below the image
        file_size_kb = len(complete_doc_data) / 1024  # Calculate file size in KB
        metadata_text = f"{file_name} - {file_size_kb:.2f} KB"
        chat_log.insert(tk.END, metadata_text + "\n", "gray")
        chat_log.tag_configure("gray", foreground="gray")

        # Scroll and disable chat log
        chat_log.yview(tk.END)
        chat_log.config(state=tk.DISABLED)

        # Keep a reference to avoid garbage collection
        image_references.append(photo)

        # Bind the click event to the image label to save the document
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
            chat_log.insert(tk.END, f"{sender_ip} (you): \n", ("sent_message",))
        else:
            chat_log.insert(tk.END, f"{sender_ip}: \n", ("sent_message",))

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
        chat_log.insert(tk.END, f"{sender_ip} (you): \n", ("sent_message",))
    else:
        chat_log.insert(tk.END, f"{sender_ip}: \n", ("sent_message",))

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

# Function to check if a file is a supported image type by Pillow
def is_supported_image(file_path):
    try:
        with Image.open(file_path) as img:
            img.verify()  # Verify if it's a valid image file
        return True
    except Exception:
        return False

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
        if is_supported_image(file):  # Check if the file is a supported image
            send_image_over_udp(file)  # Call image sending function
        else:
            send_document_over_udp(file)  # Call document sending function

# Ensure the chat log auto-scrolls to the newest message after adding any message
def auto_scroll_chat_log():
    chat_log.yview_moveto(1.0)  # Move scrollbar to the bottom

def copy_to_clipboard(event=None):
    # Copy the selected text to the clipboard
    chat_log.clipboard_clear()
    try:
        chat_log.clipboard_append(chat_log.get("sel.first", "sel.last"))
        chat_log.update()  # Update clipboard to ensure it's available
    except tk.TclError:
        pass  # Handle the case where no text is selected

def show_context_menu(event):
    # Display the context menu at the mouse pointer position
    context_menu.post(event.x_root, event.y_root)

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

upload_frame = tk.Frame(root)
upload_frame.pack(fill=tk.X, pady=5)

# Create the context menu
context_menu = tk.Menu(frame, tearoff=0)
context_menu.add_command(label="Copy", command=copy_to_clipboard)

# Bind right-click event to show the context menu
chat_log.bind("<Button-3>", show_context_menu)

# Allow copying with Ctrl+C
chat_log.bind("<Control-c>", copy_to_clipboard)

# Optionally, you can also bind Ctrl+Insert for copying
chat_log.bind("<Control-Insert>", copy_to_clipboard)

input_frame = tk.Frame(root)
input_frame.pack(pady=5, padx=10, fill=tk.X)

upload_frame.pack_forget()

# Add settings button to the left inside the input frame
settings_button = tk.Button(input_frame, text="⚙️", command=open_settings)
settings_button.pack(side=tk.LEFT, padx=5)

# Shrink the entry box to allow space for the settings button
entry = tk.Entry(input_frame, width=40)  # Reduced width
entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

# Send button and other options remain unchanged
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

chat_log.tag_configure("sent_message", foreground=sent_message_color)
chat_log.tag_configure("received_message", foreground=received_message_color)

# Setup UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('', UDP_PORT))

# Increase socket buffer size
sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65535)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65535)

# Start the queue processing function
root.after(100, process_queue)

# Start receiving thread
recv_thread = threading.Thread(target=receive, daemon=True)
recv_thread.start()

# Start GUI event loop
root.mainloop()

# Close socket when exiting
sock.close()
