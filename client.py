import socket
import os
import hashlib
import json
import sys
import time
import logging
from logging.handlers import RotatingFileHandler


class FileClient:
    def __init__(self, host='localhost', port=5000, download_dir='client_downloads', log_dir='client_logs'):
        """Initialize the file client with server address and download directory"""
        self.host = host
        self.port = port
        self.download_dir = download_dir
        self.log_dir = log_dir
        self.socket = None
        
        # Create required directories if they don't exist
        for directory in [download_dir, log_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                
        # Setup logging
        self.setup_logging()
        self.logger.info("Client initialized")
    
    def setup_logging(self):
        """Setup the logging configuration for the client"""
        self.logger = logging.getLogger('FileClient')
        self.logger.setLevel(logging.INFO)
        
        # Create log format
        log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # Create a handler for console output
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_format)
        self.logger.addHandler(console_handler)
        
        # Create a handler for file output with rotation (max 5MB per file, max 5 backup files)
        log_file = os.path.join(self.log_dir, 'client.log')
        file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
        file_handler.setFormatter(log_format)
        self.logger.addHandler(file_handler)
    
    def connect(self):
        """Connect to the file server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.logger.info(f"Connected to server at {self.host}:{self.port}")
            print(f"Connected to server at {self.host}:{self.port}")
            return True
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            print(f"Connection failed: {e}")
            return False
    
    def close(self):
        """Close the connection to the server"""
        if self.socket:
            self.socket.close()
            self.socket = None
            self.logger.info("Connection closed")
            print("Connection closed")
    
    def send_request(self, request_data):
        """Send a request to the server and receive the response"""
        if not self.socket:
            self.logger.error("Not connected to server")
            print("Not connected to server")
            return None
        
        # Send request
        request = json.dumps(request_data).encode('utf-8')
        self.socket.sendall(request)
        self.logger.debug(f"Sent request: {request_data}")
        
        # Receive response
        response_data = self.socket.recv(4096).decode('utf-8')
        try:
            response = json.loads(response_data)
            self.logger.debug(f"Received response: {response}")
            return response
        except json.JSONDecodeError:
            self.logger.error("Invalid response from server")
            print("Error: Invalid response from server")
            return None
    
    def upload_file(self, filepath, handling_mode='overwrite'):
        """
        Upload a file to the server
        
        Args:
            filepath: Path to the file to upload
            handling_mode: How to handle duplicates - 'overwrite', 'rename', or 'versioning'
        """
        if not os.path.exists(filepath):
            self.logger.error(f"File {filepath} not found")
            print(f"Error: File {filepath} not found")
            return False
        
        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)
        
        self.logger.info(f"Preparing to upload {filename} ({filesize} bytes), mode: {handling_mode}")
        
        # Calculate file hash
        hash_obj = hashlib.sha256()
        with open(filepath, 'rb') as f:
            while True:
                data = f.read(4096)
                if not data:
                    break
                hash_obj.update(data)
        
        file_hash = hash_obj.hexdigest()
        
        # Send upload request
        request = {
            'command': 'UPLOAD',
            'filename': filename,
            'filesize': filesize,
            'hash': file_hash,
            'handling_mode': handling_mode
        }
        
        response = self.send_request(request)
        if not response or response.get('status') != 'ready':
            self.logger.error(f"Server not ready to receive file: {response}")
            print(f"Error: Server not ready to receive file")
            return False
        
        # Check if file was renamed
        new_filename = response.get('filename', filename)
        is_duplicate = response.get('is_duplicate', False)
        actual_handling_mode = response.get('handling_mode', handling_mode)
        
        if is_duplicate:
            if actual_handling_mode == 'rename' and new_filename != filename:
                self.logger.info(f"File already exists, renamed to {new_filename}")
                print(f"File already exists, renamed to {new_filename}")
            elif actual_handling_mode == 'versioning':
                self.logger.info(f"File already exists, previous version archived")
                print(f"File already exists, previous version archived")
            else:
                self.logger.info(f"File already exists, will be overwritten")
                print(f"File already exists, will be overwritten")
        
        # Send file data
        sent = 0
        start_time = time.time()
        
        with open(filepath, 'rb') as f:
            while sent < filesize:
                # Read file in chunks of 4096 bytes
                chunk = f.read(4096)
                if not chunk:
                    break
                
                # Send chunk
                self.socket.sendall(chunk)
                sent += len(chunk)
                
                # Print progress
                progress = (sent / filesize) * 100
                elapsed_time = time.time() - start_time
                speed = sent / (elapsed_time if elapsed_time > 0 else 1)
                sys.stdout.write(f"\rUploading: {progress:.1f}% - {speed/1024:.1f} KB/s")
                sys.stdout.flush()
        
        print("\nWaiting for server confirmation...")
        
        # Get upload confirmation
        response_data = self.socket.recv(4096).decode('utf-8')
        try:
            response = json.loads(response_data)
            if response.get('status') == 'success':
                self.logger.info(f"File {new_filename} uploaded successfully")
                print(f"\nFile {new_filename} uploaded successfully!")
                return True
            else:
                error_msg = response.get('message', 'Unknown error')
                self.logger.error(f"Upload failed: {error_msg}")
                print(f"\nError: {error_msg}")
                return False
        except json.JSONDecodeError:
            self.logger.error("Invalid response from server after upload")
            print("\nError: Invalid response from server")
            return False
    
    def download_file(self, filename):
        """Download a file from the server"""
        self.logger.info(f"Requesting download of {filename}")
        
        # Send download request
        request = {
            'command': 'DOWNLOAD',
            'filename': filename
        }
        
        response = self.send_request(request)
        if not response:
            return False
        
        if response.get('status') != 'ready':
            error_msg = response.get('message', 'Server not ready')
            self.logger.error(f"Download failed: {error_msg}")
            print(f"Error: {error_msg}")
            return False
        
        # Get file info
        filesize = response.get('filesize')
        file_hash = response.get('hash')
        
        if not all([filesize, file_hash]):
            self.logger.error("Missing file information from server")
            print("Error: Missing file information from server")
            return False
        
        # Send ready to receive
        ready_msg = json.dumps({'status': 'ready'}).encode('utf-8')
        self.socket.sendall(ready_msg)
        
        # Prepare to receive file
        filepath = os.path.join(self.download_dir, filename)
        received = 0
        hash_obj = hashlib.sha256()
        start_time = time.time()
        
        with open(filepath, 'wb') as f:
            while received < filesize:
                # Receive data in chunks
                chunk = self.socket.recv(min(4096, filesize - received))
                if not chunk:
                    break
                
                # Update hash
                hash_obj.update(chunk)
                
                # Write chunk to file
                f.write(chunk)
                received += len(chunk)
                
                # Print progress
                progress = (received / filesize) * 100
                elapsed_time = time.time() - start_time
                speed = received / (elapsed_time if elapsed_time > 0 else 1)
                sys.stdout.write(f"\rDownloading: {progress:.1f}% - {speed/1024:.1f} KB/s")
                sys.stdout.flush()
        
        print("\nVerifying file integrity...")
        
        # Verify file integrity
        calculated_hash = hash_obj.hexdigest()
        if calculated_hash == file_hash:
            self.logger.info(f"File {filename} downloaded successfully")
            print(f"\nFile {filename} downloaded successfully!")
            return True
        else:
            # Remove corrupted file
            os.remove(filepath)
            self.logger.error(f"File corruption detected for {filename}")
            print("\nError: File corruption detected")
            print(f"Expected hash: {file_hash}")
            print(f"Received hash: {calculated_hash}")
            return False
    
    def list_files(self):
        """List files available on the server"""
        self.logger.info("Requesting file list from server")
        request = {'command': 'LIST'}
        response = self.send_request(request)
        
        if not response:
            return []
        
        if response.get('status') != 'success':
            error_msg = response.get('message', 'Unknown error')
            self.logger.error(f"Failed to get file list: {error_msg}")
            print(f"Error: {error_msg}")
            return []
        
        files = response.get('files', [])
        
        if not files:
            print("No files available on the server")
        else:
            print("\nFiles available on the server:")
            print("-" * 80)
            print(f"{'Filename':<30} {'Size':<10} {'Modified':<20} {'Versions':<10}")
            print("-" * 80)
            
            for file_info in files:
                filename = file_info.get('filename')
                size = file_info.get('size', 0)
                modified = file_info.get('modified', 'Unknown')
                version_count = len(file_info.get('versions', []))
                
                # Format size
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size/1024:.1f} KB"
                else:
                    size_str = f"{size/(1024*1024):.1f} MB"
                
                print(f"{filename:<30} {size_str:<10} {modified:<20} {version_count:<10}")
            
            print("-" * 80)
            
            self.logger.info(f"Received list of {len(files)} files from server")
        
        return files
    
    def view_file_versions(self, filename):
        """View version history of a specific file"""
        self.logger.info(f"Viewing version history for {filename}")
        request = {'command': 'LIST'}
        response = self.send_request(request)
        
        if not response or response.get('status') != 'success':
            self.logger.error("Failed to get file list")
            print("Error: Failed to get file list")
            return
        
        files = response.get('files', [])
        file_info = None
        
        # Find the file with the specified name
        for file in files:
            if file.get('filename') == filename:
                file_info = file
                break
        
        if not file_info:
            self.logger.error(f"File {filename} not found")
            print(f"Error: File {filename} not found")
            return
        
        versions = file_info.get('versions', [])
        
        if not versions:
            print(f"No version history available for {filename}")
            return
        
        print(f"\nVersion history for {filename}:")
        print("-" * 80)
        print(f"{'Version':<40} {'Size':<10} {'Modified':<20}")
        print("-" * 80)
        
        for version in versions:
            ver_filename = version.get('filename')
            ver_size = version.get('size', 0)
            ver_modified = version.get('modified', 'Unknown')
            
            # Format size
            if ver_size < 1024:
                size_str = f"{ver_size} B"
            elif ver_size < 1024 * 1024:
                size_str = f"{ver_size/1024:.1f} KB"
            else:
                size_str = f"{ver_size/(1024*1024):.1f} MB"
            
            print(f"{ver_filename:<40} {size_str:<10} {ver_modified:<20}")
        
        print("-" * 80)
        self.logger.info(f"Displayed {len(versions)} versions for {filename}")


def main():
    """Main function to run the client"""
    # Default settings
    host = 'localhost'
    port = 5000
    
    # Create client
    client = FileClient(host=host, port=port)
    
    while True:
        print("\nFile Transfer Client")
        print("-------------------")
        print("1. Connect to server")
        print("2. Upload file")
        print("3. Download file")
        print("4. List files")
        print("5. View file versions")
        print("6. Exit")
        
        choice = input("\nEnter your choice (1-6): ")
        
        if choice == '1':
            if client.socket:
                print("Already connected to server")
            else:
                client.connect()
        
        elif choice == '2':
            if not client.socket:
                print("Not connected to server. Connecting...")
                if not client.connect():
                    continue
            
            filepath = input("Enter the path to the file you want to upload: ")
            
            # Ask for duplicate handling preference
            print("\nHow should duplicates be handled?")
            print("1. Overwrite existing file")
            print("2. Rename new file (e.g. filename_v2.txt)")
            print("3. Keep version history of previous files")
            
            dup_choice = input("Enter your choice (1-3): ")
            
            handling_mode = 'overwrite'
            if dup_choice == '2':
                handling_mode = 'rename'
            elif dup_choice == '3':
                handling_mode = 'versioning'
            
            client.upload_file(filepath, handling_mode)
        
        elif choice == '3':
            if not client.socket:
                print("Not connected to server. Connecting...")
                if not client.connect():
                    continue
            
            client.list_files()
            filename = input("Enter the name of the file you want to download: ")
            client.download_file(filename)
        
        elif choice == '4':
            if not client.socket:
                print("Not connected to server. Connecting...")
                if not client.connect():
                    continue
            
            client.list_files()
        
        elif choice == '5':
            if not client.socket:
                print("Not connected to server. Connecting...")
                if not client.connect():
                    continue
            
            client.list_files()
            filename = input("Enter the name of the file to view versions: ")
            client.view_file_versions(filename)
        
        elif choice == '6':
            print("Exiting...")
            client.close()
            break
        
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
