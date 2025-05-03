import socket
import os
import hashlib
import json
import sys
import time
import logging
from logging.handlers import RotatingFileHandler


# FileClient class handles all client-side operations for the TCP file sharing system
# It manages server connections, file uploads/downloads, and communicates with the server
class FileClient:
    def __init__(self, host='localhost', port=5000, download_dir='client_downloads', log_dir='client_logs'):
        """Initialize the file client with server address and download directory

        Args:
            host (str): Server hostname or IP address (default: localhost)
            port (int): Server port number (default: 5000)
            download_dir (str): Directory to store downloaded files
            log_dir (str): Directory to store client logs
        """
        self.host = host
        self.port = port
        self.download_dir = download_dir
        self.log_dir = log_dir
        self.socket = None

        # Create required directories if they don't exist
        # This ensures we can save downloads and logs without manual setup
        for directory in [download_dir, log_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)

        # Setup logging system with file and console handlers
        self.setup_logging()
        self.logger.info("Client initialized")

    def setup_logging(self):
        """Setup the logging configuration for the client

        Creates a logger with both console and file output.
        File logs use rotation to prevent excessive disk usage.
        """
        self.logger = logging.getLogger('FileClient')
        self.logger.setLevel(logging.INFO)

        # Create log format with timestamp, level, and message
        log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # Create a handler for console output
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_format)
        self.logger.addHandler(console_handler)

        # Create a handler for file output with rotation (max 5MB per file, max 5 backup files)
        # This prevents logs from consuming too much disk space
        log_file = os.path.join(self.log_dir, 'client.log')
        file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5)
        file_handler.setFormatter(log_format)
        self.logger.addHandler(file_handler)

    def connect(self):
        """Connect to the file server

        Establishes a TCP socket connection to the specified server host and port.
        Includes error handling for timeouts and connection refusals.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Close any existing connection first
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None

            # Create a new TCP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Set timeout to prevent indefinite hanging during connection attempts
            self.socket.settimeout(30)  # 30 seconds timeout for connection
            self.socket.connect((self.host, self.port))
            # After connection is established, set a longer timeout for operations
            self.socket.settimeout(300)  # 5 minutes for operations
            self.logger.info(f"Connected to server at {self.host}:{self.port}")
            print(f"Connected to server at {self.host}:{self.port}")
            return True
        except socket.timeout:
            # Handle connection timeout (server not responding)
            self.logger.error(f"Connection timed out: Server at {self.host}:{self.port} is not responding")
            print(f"Connection timed out: Server at {self.host}:{self.port} is not responding")
            return False
        except ConnectionRefusedError:
            # Handle connection refused (server not running or wrong port)
            self.logger.error(
                f"Connection refused: Server at {self.host}:{self.port} is not running or the port is incorrect")
            print(f"Connection refused: Server at {self.host}:{self.port} is not running or the port is incorrect")
            return False
        except Exception as e:
            # Handle any other connection errors
            self.logger.error(f"Connection failed: {e}")
            print(f"Connection failed: {e}")
            return False

    def close(self):
        """Close the connection to the server

        Properly closes the socket connection and resets the socket attribute.
        """
        if self.socket:
            self.socket.close()
            self.socket = None
            self.logger.info("Connection closed")
            print("Connection closed")

    def send_request(self, request_data):
        """Send a request to the server and receive the response

        This is the core communication method that handles JSON serialization,
        network transmission, and response parsing. Includes retry logic for
        transient network errors.

        Args:
            request_data (dict): Dictionary containing the request parameters

        Returns:
            dict: The parsed JSON response from the server, or None if communication failed
        """
        if not self.socket:
            self.logger.error("Not connected to server")
            print("Not connected to server")
            return None

        # Number of retries for transient errors
        retries = 2
        retry_count = 0

        while retry_count <= retries:
            try:
                # Serialize request to JSON and send it
                request = json.dumps(request_data).encode('utf-8')
                self.socket.sendall(request)
                self.logger.debug(f"Sent request: {request_data}")

                # Receive and parse response
                response_data = self.socket.recv(4096).decode('utf-8')
                if not response_data:
                    raise ConnectionError("Empty response received from server")

                try:
                    # Parse JSON response
                    response = json.loads(response_data)
                    self.logger.debug(f"Received response: {response}")
                    return response
                except json.JSONDecodeError:
                    # Handle invalid JSON in response
                    self.logger.error("Invalid response from server")
                    print("Error: Invalid response from server")
                    return None

            except (socket.timeout, ConnectionError) as e:
                # Handle timeout and connection errors with retry logic
                retry_count += 1
                if retry_count <= retries:
                    self.logger.warning(f"Communication error: {e}. Retrying ({retry_count}/{retries})...")
                    print(f"Communication error. Retrying ({retry_count}/{retries})...")
                    # Short delay before retry to allow network recovery
                    time.sleep(1)
                    continue
                else:
                    # All retries failed
                    self.logger.error(f"Communication failed after {retries} retries: {e}")
                    print(f"Error: Communication with server failed after {retries} retries")
                    # Try to reconnect as a last resort
                    self.close()
                    if self.connect():
                        print("Reconnected to server. Please try again.")
                    return None
            except Exception as e:
                # Handle any other unexpected errors
                self.logger.error(f"Unexpected error in communication: {e}")
                print(f"Error: {e}")
                return None

    def upload_file(self, filepath, handling_mode='overwrite'):
        """
        Upload a file to the server

        This method handles the complete file upload process:
        1. Validates the file exists locally
        2. Calculates the file's SHA-256 hash
        3. Negotiates upload with the server
        4. Sends the file data in chunks
        5. Displays progress during upload
        6. Verifies successful upload with server confirmation

        Args:
            filepath: Path to the file to upload
            handling_mode: How to handle duplicates - 'overwrite', 'rename', or 'versioning'

        Returns:
            bool: True if upload successful, False otherwise
        """
        # Verify file exists
        if not os.path.exists(filepath):
            self.logger.error(f"File {filepath} not found")
            print(f"Error: File {filepath} not found")
            return False

        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)

        self.logger.info(f"Preparing to upload {filename} ({filesize} bytes), mode: {handling_mode}")

        # Calculate file hash (SHA-256) for integrity verification
        hash_obj = hashlib.sha256()
        with open(filepath, 'rb') as f:
            while True:
                data = f.read(4096)
                if not data:
                    break
                hash_obj.update(data)

        file_hash = hash_obj.hexdigest()

        # Send upload request with file metadata
        request = {
            'command': 'UPLOAD',
            'filename': filename,
            'filesize': filesize,
            'hash': file_hash,
            'handling_mode': handling_mode
        }

        # Get server response (ready to receive or error)
        response = self.send_request(request)
        if not response or response.get('status') != 'ready':
            self.logger.error(f"Server not ready to receive file: {response}")
            print(f"Error: Server not ready to receive file")
            return False

        # Check if file was renamed due to duplicate handling
        new_filename = response.get('filename', filename)
        is_duplicate = response.get('is_duplicate', False)
        actual_handling_mode = response.get('handling_mode', handling_mode)

        # Inform user about duplicate handling decisions
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

        # Send file data in chunks, tracking progress
        sent = 0
        start_time = time.time()

        try:
            with open(filepath, 'rb') as f:
                while sent < filesize:
                    # Read file in chunks of 4096 bytes
                    chunk = f.read(4096)
                    if not chunk:
                        break

                    try:
                        # Send chunk to server
                        self.socket.sendall(chunk)
                        sent += len(chunk)

                        # Display progress with percentage and speed
                        progress = (sent / filesize) * 100
                        elapsed_time = time.time() - start_time
                        speed = sent / (elapsed_time if elapsed_time > 0 else 1)
                        sys.stdout.write(f"\rUploading: {progress:.1f}% - {speed / 1024:.1f} KB/s")
                        sys.stdout.flush()
                    except socket.timeout:
                        raise Exception("Upload timed out. Server not responding.")
                    except socket.error as e:
                        raise Exception(f"Network error during upload: {e}")

            print("\nWaiting for server confirmation...")

            # Get upload confirmation from server
            try:
                response_data = self.socket.recv(4096).decode('utf-8')
                try:
                    response = json.loads(response_data)
                    if response.get('status') == 'success':
                        # Upload succeeded
                        self.logger.info(f"File {new_filename} uploaded successfully")
                        print(f"\nFile {new_filename} uploaded successfully!")
                        return True
                    else:
                        # Upload failed with error from server
                        error_msg = response.get('message', 'Unknown error')
                        self.logger.error(f"Upload failed: {error_msg}")
                        print(f"\nError: {error_msg}")
                        return False
                except json.JSONDecodeError:
                    # Invalid response format
                    self.logger.error("Invalid response from server after upload")
                    print("\nError: Invalid response from server")
                    return False
            except socket.timeout:
                # No confirmation received in time
                self.logger.error("Timed out waiting for server confirmation")
                print(
                    "\nError: Timed out waiting for server confirmation. The file may have been uploaded but the confirmation was not received.")
                return False
            except Exception as e:
                # Other error during confirmation
                self.logger.error(f"Error receiving confirmation: {e}")
                print(f"\nError receiving confirmation: {e}")
                return False

        except Exception as e:
            # Handle upload process errors
            self.logger.error(f"Upload failed: {e}")
            print(f"\nUpload failed: {e}")
            return False

    def download_file(self, filename):
        """Download a file from the server

        This method handles the complete file download process:
        1. Requests the file from the server
        2. Receives file metadata (size, hash)
        3. Receives the file data in chunks
        4. Displays progress during download
        5. Verifies file integrity with hash comparison
        6. Handles timeouts with resume capability

        Args:
            filename: Name of the file to download from the server

        Returns:
            bool: True if download successful, False otherwise
        """
        self.logger.info(f"Requesting download of {filename}")

        # Send download request
        request = {
            'command': 'DOWNLOAD',
            'filename': filename
        }

        # Get server response
        response = self.send_request(request)
        if not response:
            return False

        # Check if server is ready to send file
        if response.get('status') != 'ready':
            error_msg = response.get('message', 'Server not ready')
            self.logger.error(f"Download failed: {error_msg}")
            print(f"Error: {error_msg}")
            return False

        # Extract file metadata
        filesize = response.get('filesize')
        file_hash = response.get('hash')

        # Validate required metadata is present
        if not all([filesize, file_hash]):
            self.logger.error("Missing file information from server")
            print("Error: Missing file information from server")
            return False

        # Send ready confirmation to begin receiving file
        ready_msg = json.dumps({'status': 'ready'}).encode('utf-8')
        self.socket.sendall(ready_msg)

        # Prepare to receive file
        filepath = os.path.join(self.download_dir, filename)
        received = 0
        hash_obj = hashlib.sha256()
        start_time = time.time()

        try:
            # Open file for writing binary data
            with open(filepath, 'wb') as f:
                last_progress_update = 0
                # Receive file in chunks until complete
                while received < filesize:
                    try:
                        # Receive data in chunks (adjust size for final chunk)
                        chunk = self.socket.recv(min(4096, filesize - received))
                        if not chunk:
                            # Connection closed unexpectedly
                            raise Exception("Connection closed during file transfer")

                        # Update hash for integrity verification
                        hash_obj.update(chunk)

                        # Write chunk to file
                        f.write(chunk)
                        received += len(chunk)

                        # Display progress (update every ~1% to reduce console spam)
                        progress = (received / filesize) * 100
                        if progress - last_progress_update >= 1 or progress >= 100:
                            elapsed_time = time.time() - start_time
                            speed = received / (elapsed_time if elapsed_time > 0 else 1)
                            sys.stdout.write(f"\rDownloading: {progress:.1f}% - {speed / 1024:.1f} KB/s")
                            sys.stdout.flush()
                            last_progress_update = progress
                    except socket.timeout:
                        # Handle download timeout with resume capability
                        remaining = filesize - received
                        print(
                            f"\nWarning: Download timed out. {received}/{filesize} bytes received ({(received / filesize) * 100:.1f}%). Trying to resume...")

                        # Try to reconnect and resume from current offset
                        if not self.reconnect_and_resume_download(filename, received):
                            raise Exception("Failed to resume download after timeout")
                    except socket.error as e:
                        # Handle other network errors
                        raise Exception(f"Network error during download: {e}")

            print("\nVerifying file integrity...")

            # Verify file integrity by comparing hashes
            calculated_hash = hash_obj.hexdigest()
            if calculated_hash == file_hash:
                # Success - hashes match
                self.logger.info(f"File {filename} downloaded successfully")
                print(f"\nFile {filename} downloaded successfully!")
                return True
            else:
                # Failure - hashes don't match, file is corrupted
                os.remove(filepath)
                self.logger.error(f"File corruption detected for {filename}")
                print("\nError: File corruption detected")
                print(f"Expected hash: {file_hash}")
                print(f"Received hash: {calculated_hash}")
                return False
        except Exception as e:
            # Handle download process errors
            self.logger.error(f"Download failed: {e}")
            print(f"\nDownload failed: {e}")

            # Clean up partial file
            try:
                f.close()
            except:
                pass

            if os.path.exists(filepath):
                os.remove(filepath)

            return False

    def reconnect_and_resume_download(self, filename, offset):
        """
        Attempt to reconnect to the server and resume a download

        This method is called when a download is interrupted and handles:
        1. Reconnecting to the server
        2. Requesting the same file with a resume offset
        3. Preparing to continue receiving from where it left off

        Args:
            filename: The name of the file being downloaded
            offset: The offset to resume from (bytes already received)

        Returns:
            bool: True if successful, False otherwise
        """
        self.logger.info(f"Attempting to resume download of {filename} from offset {offset}")

        # Close the existing connection if it exists
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

        # Try to reconnect to server
        if not self.connect():
            self.logger.error("Failed to reconnect to server")
            return False

        # Send resume request with offset
        request = {
            'command': 'DOWNLOAD',
            'filename': filename,
            'resume_offset': offset
        }

        # Get server response
        response = self.send_request(request)
        if not response or response.get('status') != 'ready':
            self.logger.error("Server not ready to resume download")
            return False

        # Send ready to receive confirmation
        ready_msg = json.dumps({'status': 'ready'}).encode('utf-8')
        self.socket.sendall(ready_msg)

        return True

    def list_files(self):
        """List files available on the server

        Requests and displays a formatted list of files available on the server,
        including their sizes, modification times, and version counts.

        Returns:
            list: List of file information dictionaries from the server
        """
        self.logger.info("Requesting file list from server")
        request = {'command': 'LIST'}
        response = self.send_request(request)

        if not response:
            return []

        # Check for success status
        if response.get('status') != 'success':
            error_msg = response.get('message', 'Unknown error')
            self.logger.error(f"Failed to get file list: {error_msg}")
            print(f"Error: {error_msg}")
            return []

        # Extract file list from response
        files = response.get('files', [])

        # Display file list in a formatted table
        if not files:
            print("No files available on the server")
        else:
            print("\nFiles available on the server:")
            print("-" * 80)
            print(f"{'Filename':<30} {'Size':<10} {'Modified':<20} {'Versions':<10}")
            print("-" * 80)

            # Display each file's information
            for file_info in files:
                filename = file_info.get('filename')
                size = file_info.get('size', 0)
                modified = file_info.get('modified', 'Unknown')
                version_count = len(file_info.get('versions', []))

                # Format size for human readability (B, KB, MB)
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"

                print(f"{filename:<30} {size_str:<10} {modified:<20} {version_count:<10}")

            print("-" * 80)

            self.logger.info(f"Received list of {len(files)} files from server")

        return files

    def view_file_versions(self, filename):
        """View version history of a specific file

        Retrieves and displays all available versions of a specified file,
        including their names, sizes, and modification times.

        Args:
            filename: The name of the file to show version history for
        """
        self.logger.info(f"Viewing version history for {filename}")
        # Get file list which includes version information
        request = {'command': 'LIST'}
        response = self.send_request(request)

        if not response or response.get('status') != 'success':
            self.logger.error("Failed to get file list")
            print("Error: Failed to get file list")
            return

        files = response.get('files', [])
        file_info = None

        # Find the specific file in the list
        for file in files:
            if file.get('filename') == filename:
                file_info = file
                break

        if not file_info:
            self.logger.error(f"File {filename} not found")
            print(f"Error: File {filename} not found")
            return

        # Get version history for this file
        versions = file_info.get('versions', [])

        # Display version information in a formatted table
        if not versions:
            print(f"No version history available for {filename}")
            return

        print(f"\nVersion history for {filename}:")
        print("-" * 80)
        print(f"{'Version':<40} {'Size':<10} {'Modified':<20}")
        print("-" * 80)

        # Display each version's information
        for version in versions:
            ver_filename = version.get('filename')
            ver_size = version.get('size', 0)
            ver_modified = version.get('modified', 'Unknown')

            # Format size for human readability (B, KB, MB)
            if ver_size < 1024:
                size_str = f"{ver_size} B"
            elif ver_size < 1024 * 1024:
                size_str = f"{ver_size / 1024:.1f} KB"
            else:
                size_str = f"{ver_size / (1024 * 1024):.1f} MB"

            print(f"{ver_filename:<40} {size_str:<10} {ver_modified:<20}")

        print("-" * 80)
        self.logger.info(f"Displayed {len(versions)} versions for {filename}")


# Main function provides a command-line interface for the FileClient
def main():
    """Main function to run the client

    Provides a text-based menu interface for the user to interact with
    the file transfer client, including connecting to a server and
    performing file operations.
    """
    # Default settings for server connection
    host = 'localhost'
    port = 5000

    print("\nFile Transfer Client")
    print("=" * 60)

    # Allow user to specify custom server address
    custom_server = input("Do you want to connect to a custom server? (y/n) [n]: ").lower().strip()
    if custom_server == 'y':
        host = input("Enter server hostname or IP [localhost]: ").strip() or 'localhost'
        try:
            port_input = input("Enter server port [5000]: ").strip() or '5000'
            port = int(port_input)
        except ValueError:
            print("Invalid port number. Using default port 5000.")
            port = 5000

    # Create client instance
    client = FileClient(host=host, port=port)

    # Main menu loop
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
            # Option 1: Connect to server
            if client.socket:
                print("Already connected to server")
            else:
                client.connect()

        elif choice == '2':
            # Option 2: Upload file
            # Auto-connect if not already connected
            if not client.socket:
                print("Not connected to server. Connecting...")
                if not client.connect():
                    continue

            # Get file path from user
            filepath = input("Enter the path to the file you want to upload: ")

            # Ask for duplicate handling preference
            print("\nHow should duplicates be handled?")
            print("1. Overwrite existing file")
            print("2. Rename new file (e.g. filename_v2.txt)")
            print("3. Keep version history of previous files")

            dup_choice = input("Enter your choice (1-3): ")

            # Set handling mode based on user choice
            handling_mode = 'overwrite'
            if dup_choice == '2':
                handling_mode = 'rename'
            elif dup_choice == '3':
                handling_mode = 'versioning'

            # Upload the file with the selected handling mode
            client.upload_file(filepath, handling_mode)

        elif choice == '3':
            # Option 3: Download file
            # Auto-connect if not already connected
            if not client.socket:
                print("Not connected to server. Connecting...")
                if not client.connect():
                    continue

            # Show available files and get filename from user
            client.list_files()
            filename = input("Enter the name of the file you want to download: ")
            client.download_file(filename)

        elif choice == '4':
            # Option 4: List files
            # Auto-connect if not already connected
            if not client.socket:
                print("Not connected to server. Connecting...")
                if not client.connect():
                    continue

            # Display list of files on server
            client.list_files()

        elif choice == '5':
            # Option 5: View file versions
            # Auto-connect if not already connected
            if not client.socket:
                print("Not connected to server. Connecting...")
                if not client.connect():
                    continue

            # Show available files and get filename from user
            client.list_files()
            filename = input("Enter the name of the file to view versions: ")
            client.view_file_versions(filename)

        elif choice == '6':
            # Option 6: Exit the client
            print("Exiting...")
            client.close()
            break

        else:
            # Handle invalid menu choices
            print("Invalid choice. Please try again.")


# Entry point for running the client directly
if __name__ == "__main__":
    main()