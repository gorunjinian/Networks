import socket
import threading
import os
import hashlib
import json
import logging
import datetime
import shutil
from logging.handlers import RotatingFileHandler
import time


# FileServer class is the main implementation of a TCP socket-based file server
# It handles client connections, file upload/download operations, and version management
class FileServer:
    def __init__(self, host='0.0.0.0', port=5000, storage_dir='server_storage',
                 log_dir='server_logs', version_dir='version_history'):
        """Initialize the file server with host, port and storage directory

        Args:
            host (str): The host address to bind to (0.0.0.0 means all interfaces)
            port (int): The port number to listen on
            storage_dir (str): Directory to store uploaded files
            log_dir (str): Directory to store server logs
            version_dir (str): Subdirectory within storage_dir for version history
        """
        self.host = host
        self.port = port
        self.storage_dir = storage_dir
        self.log_dir = log_dir
        self.version_dir = os.path.join(storage_dir, version_dir)
        self.socket = None

        # Create required directories if they don't exist
        # This ensures the server can operate without manual directory setup
        for directory in [storage_dir, log_dir, self.version_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)

        # Setup logging system with file and console handlers
        self.setup_logging()
        self.logger.info("Server initialized")

    def setup_logging(self):
        """Setup the logging configuration for the server

        Creates a logger with both console and file output.
        File logs use rotation to prevent excessive disk usage.
        """
        self.logger = logging.getLogger('FileServer')
        self.logger.setLevel(logging.INFO)

        # Create log format with timestamp, level, and message
        log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # Create a handler for console output (useful for monitoring)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_format)
        self.logger.addHandler(console_handler)

        # Create a handler for file output with rotation (max 5MB per file, max 5 backup files)
        # This prevents logs from consuming too much disk space
        log_file = os.path.join(self.log_dir, 'server.log')
        file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5)
        file_handler.setFormatter(log_format)
        self.logger.addHandler(file_handler)

    def start(self):
        """Start the server and listen for client connections

        Creates a TCP socket, binds to the specified host/port,
        and enters the main connection acceptance loop.
        Each client connection spawns a new thread.
        """
        # Create a TCP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Set socket option to allow reuse of the address (prevents "Address already in use" errors)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            # Bind the socket to the host and port
            self.socket.bind((self.host, self.port))
            # Listen for incoming connections (queue up to 5 connections)
            self.socket.listen(5)
            self.logger.info(f"Server started on {self.host}:{self.port}")
            print(f"Server started on {self.host}:{self.port}")
            print(f"Files will be stored in {os.path.abspath(self.storage_dir)}")
            print(f"Logs will be stored in {os.path.abspath(self.log_dir)}")

            # Main server loop - continuously accept new connections
            while True:
                try:
                    # Accept a client connection
                    client_socket, address = self.socket.accept()
                    # Set a timeout for socket operations (5 minutes)
                    # This prevents hanging connections that never send data
                    client_socket.settimeout(300)  # 5-minute timeout
                    self.logger.info(f"New connection from {address[0]}:{address[1]}")
                    print(f"New connection from {address[0]}:{address[1]}")

                    # Start a new thread for each client to handle multiple clients concurrently
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address)
                    )
                    # Set thread as daemon so it doesn't prevent server shutdown
                    client_thread.daemon = True
                    client_thread.start()
                except socket.error as e:
                    # Handle socket errors during connection acceptance
                    self.logger.error(f"Socket error while accepting connection: {e}")
                    continue

        except KeyboardInterrupt:
            # Handle clean shutdown with Ctrl+C
            self.logger.info("Server shutting down...")
            print("Server shutting down...")
        except Exception as e:
            # Handle other unexpected errors
            self.logger.error(f"Error: {e}")
            print(f"Error: {e}")
        finally:
            # Close the server socket on shutdown
            if self.socket:
                self.socket.close()

    def handle_client(self, client_socket, address):
        """Handle client requests in a separate thread

        Args:
            client_socket: The connected client socket object
            address: Tuple containing (IP, port) of the client

        This method runs in its own thread and handles all communication
        with a specific client until the connection is closed.
        """
        # Create a client identifier for logging
        client_id = f"{address[0]}:{address[1]}"
        self.logger.info(f"Handling client {client_id}")

        try:
            # Keep handling requests until the connection is closed
            while True:
                try:
                    # Receive request header (JSON message)
                    header_data = client_socket.recv(4096).decode('utf-8')
                    if not header_data:
                        # Empty data means the client has closed the connection
                        break

                    try:
                        # Parse the JSON request
                        request = json.loads(header_data)
                        command = request.get('command')

                        self.logger.info(f"Received command '{command}' from {client_id}")

                        # Dispatch to the appropriate handler based on the command
                        if command == 'UPLOAD':
                            self.handle_upload(client_socket, request, client_id)
                        elif command == 'DOWNLOAD':
                            self.handle_download_request(client_socket, request)
                        elif command == 'LIST':
                            self.handle_list(client_socket, client_id)
                        else:
                            # Handle unknown command
                            self.logger.warning(f"Invalid command '{command}' from {client_id}")
                            self.send_response(client_socket, {'status': 'error', 'message': 'Invalid command'})

                    except json.JSONDecodeError:
                        # Handle malformed JSON
                        self.logger.error(f"Invalid request format from {client_id}")
                        self.send_response(client_socket, {'status': 'error', 'message': 'Invalid request format'})
                except socket.timeout:
                    # Handle socket timeout (client inactive for too long)
                    self.logger.warning(f"Connection with {client_id} timed out")
                    break
                except socket.error as e:
                    # Handle socket errors (e.g., connection reset)
                    self.logger.error(f"Socket error with client {client_id}: {e}")
                    break

        except Exception as e:
            # Handle unexpected errors during client processing
            self.logger.error(f"Error handling client {client_id}: {e}")
            print(f"Error handling client {client_id}: {e}")
        finally:
            # Always ensure the socket is closed when done
            try:
                client_socket.close()
            except:
                pass
            self.logger.info(f"Connection closed with {client_id}")
            print(f"Connection closed with {client_id}")

    def check_file_exists(self, filename, handling_mode='overwrite'):
        """
        Check if a file with the same name exists and handle according to mode

        Args:
            filename: The name of the file
            handling_mode: How to handle duplicates - 'overwrite', 'rename', or 'versioning'

        Returns:
            tuple: (new_filename, is_duplicate)

        This method implements the duplicate handling strategies:
        - overwrite: Replace existing file
        - rename: Auto-append version number (e.g. file_v2.txt)
        - versioning: Keep original name but archive current version
        """
        filepath = os.path.join(self.storage_dir, filename)

        if not os.path.exists(filepath):
            # File doesn't exist, use original name
            return filename, False

        # File exists, handle according to mode
        if handling_mode == 'overwrite':
            # Overwrite mode: use same filename (will be overwritten)
            self.logger.info(f"File {filename} exists, will be overwritten")
            return filename, True

        elif handling_mode == 'rename':
            # Rename mode: find a unique name with version suffix
            name, ext = os.path.splitext(filename)
            counter = 2
            while True:
                new_filename = f"{name}_v{counter}{ext}"
                new_filepath = os.path.join(self.storage_dir, new_filename)
                if not os.path.exists(new_filepath):
                    self.logger.info(f"File {filename} exists, renamed to {new_filename}")
                    return new_filename, True
                counter += 1

        elif handling_mode == 'versioning':
            # Versioning mode: use same name but will archive the current version
            self.logger.info(f"File {filename} exists, versioning enabled")
            return filename, True

        # Default fallback if invalid handling_mode provided
        return filename, False

    def archive_existing_file(self, filename):
        """
        Archive the existing file to the version history directory

        Args:
            filename: The name of the file to archive

        Creates a timestamped version of the file in a subfolder within
        the version_history directory. The subfolder is named after the
        base filename to keep versions organized.
        """
        src_path = os.path.join(self.storage_dir, filename)
        if not os.path.exists(src_path):
            # Nothing to archive if file doesn't exist
            return

        # Create a timestamped version name (e.g. file_20230515_123045.txt)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        versioned_name = f"{name}_{timestamp}{ext}"
        dest_path = os.path.join(self.version_dir, versioned_name)

        # Create a subfolder for this file if it doesn't exist
        # This organizes versions by base filename
        file_version_dir = os.path.join(self.version_dir, name)
        if not os.path.exists(file_version_dir):
            os.makedirs(file_version_dir)

        # Copy the file to version history (preserves metadata with copy2)
        dest_path = os.path.join(file_version_dir, versioned_name)
        shutil.copy2(src_path, dest_path)
        self.logger.info(f"Archived {filename} to {dest_path}")

    def handle_upload(self, client_socket, request, client_id):
        """Handle file upload from client

        Args:
            client_socket: The client socket object
            request: Dictionary containing upload metadata
            client_id: Client identifier string for logging

        Processes a file upload request with the following steps:
        1. Extract metadata (filename, size, hash, handling mode)
        2. Handle duplicates according to the specified mode
        3. Receive the file data in chunks
        4. Verify integrity with hash comparison
        5. Send success/error response
        """
        # Extract required metadata from the request
        filename = request.get('filename')
        filesize = request.get('filesize')
        file_hash = request.get('hash')
        handling_mode = request.get('handling_mode', 'overwrite')  # Default to overwrite

        # Validate required fields are present
        if not all([filename, filesize, file_hash]):
            self.logger.error(f"Missing required information for upload from {client_id}")
            self.send_response(client_socket, {'status': 'error', 'message': 'Missing required information'})
            return

        self.logger.info(f"Upload request for {filename} ({filesize} bytes) from {client_id}")

        # Check if file already exists and handle according to mode
        try:
            new_filename, is_duplicate = self.check_file_exists(filename, handling_mode)

            # If duplicate and using versioning, archive the existing file
            if is_duplicate and handling_mode == 'versioning':
                self.archive_existing_file(filename)

            # Send ready to receive with the new filename
            self.send_response(client_socket, {
                'status': 'ready',
                'filename': new_filename,
                'is_duplicate': is_duplicate,
                'handling_mode': handling_mode
            })

            # Prepare to receive file
            filepath = os.path.join(self.storage_dir, new_filename)
            received = 0
            hash_obj = hashlib.sha256()

            # Open file for writing binary data
            with open(filepath, 'wb') as f:
                try:
                    # Receive file data in chunks until we get the full file
                    while received < filesize:
                        # Receive data in chunks of 4096 bytes (or less for final chunk)
                        chunk = client_socket.recv(min(4096, filesize - received))
                        if not chunk:
                            # Connection closed unexpectedly
                            raise Exception("Connection closed during file transfer")

                        # Update hash with this chunk
                        hash_obj.update(chunk)

                        # Write chunk to file
                        f.write(chunk)
                        received += len(chunk)
                except Exception as e:
                    # Handle errors during file transfer
                    self.logger.error(f"Error during file upload from {client_id}: {e}")
                    # Clean up the partial file
                    f.close()
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    self.send_response(client_socket, {
                        'status': 'error',
                        'message': f'File transfer error: {str(e)}'
                    })
                    return

            # Verify file integrity by comparing hashes
            calculated_hash = hash_obj.hexdigest()
            if calculated_hash == file_hash:
                # Success - hashes match
                self.logger.info(f"File {new_filename} uploaded successfully from {client_id}")
                self.send_response(client_socket, {
                    'status': 'success',
                    'message': f'File {new_filename} uploaded successfully',
                    'hash': calculated_hash
                })
            else:
                # Failure - hashes don't match, file is corrupted
                os.remove(filepath)
                self.logger.error(f"File corruption detected for {new_filename} from {client_id}")
                self.send_response(client_socket, {
                    'status': 'error',
                    'message': 'File corruption detected',
                    'expected_hash': file_hash,
                    'received_hash': calculated_hash
                })

        except Exception as e:
            # Handle any other unexpected errors
            self.logger.error(f"Unexpected error during upload from {client_id}: {e}")
            self.send_response(client_socket, {'status': 'error', 'message': f'Server error: {str(e)}'})

    def handle_download_request(self, client_socket, request):
        """Handle a client's request to download a file

        Args:
            client_socket: The client socket object
            request: Dictionary containing download request details

        Processes a file download request with these steps:
        1. Validate the requested file exists
        2. Calculate file hash for integrity verification
        3. Send file metadata to client
        4. Send the file data in chunks
        5. Support resuming from offset for interrupted downloads
        """
        # Extract request parameters
        filename = request.get('filename')
        resume_offset = request.get('resume_offset', 0)

        filepath = os.path.join(self.storage_dir, filename)

        # Check if requested file exists
        if not os.path.exists(filepath):
            self.logger.warning(f"Client requested non-existent file: {filename}")
            response = {
                'status': 'error',
                'message': f"File not found: {filename}"
            }
            self._send_response(client_socket, response)
            return

        # Get file size
        filesize = os.path.getsize(filepath)

        # Validate resume offset is within file bounds
        if resume_offset > 0:
            if resume_offset >= filesize:
                self.logger.warning(f"Invalid resume offset ({resume_offset}) for file {filename} with size {filesize}")
                response = {
                    'status': 'error',
                    'message': f"Invalid resume offset: {resume_offset}"
                }
                self._send_response(client_socket, response)
                return
            else:
                self.logger.info(f"Resuming download of {filename} from offset {resume_offset}")

        # Calculate file hash for integrity verification
        file_hash = self._calculate_file_hash(filepath)

        # Send file metadata to client
        response = {
            'status': 'ready',
            'filesize': filesize,
            'hash': file_hash,
            'resuming_from': resume_offset
        }
        self._send_response(client_socket, response)

        # Wait for client to confirm readiness
        try:
            ready_msg = client_socket.recv(1024).decode('utf-8')
            ready_data = json.loads(ready_msg)

            if ready_data.get('status') != 'ready':
                self.logger.warning(f"Client not ready to receive {filename}")
                return

            # Send file data in chunks
            with open(filepath, 'rb') as f:
                # Seek to resume position if needed
                if resume_offset > 0:
                    f.seek(resume_offset)

                # Determine how many bytes we need to send
                remaining_bytes = filesize - resume_offset

                # Track bytes sent for logging and progress reporting
                bytes_sent = 0
                start_time = time.time()
                last_log_time = start_time

                try:
                    # Send file in chunks until complete
                    while bytes_sent < remaining_bytes:
                        # Read a chunk from file
                        chunk = f.read(min(4096, remaining_bytes - bytes_sent))
                        if not chunk:
                            # End of file reached
                            break

                        # Send the chunk to client
                        client_socket.sendall(chunk)
                        bytes_sent += len(chunk)

                        # Log progress periodically (every 5 seconds or when complete)
                        current_time = time.time()
                        if current_time - last_log_time >= 5 or bytes_sent >= remaining_bytes:
                            elapsed = current_time - start_time
                            speed = bytes_sent / (elapsed if elapsed > 0 else 1)
                            percentage = (bytes_sent / remaining_bytes) * 100
                            self.logger.info(
                                f"Download progress for {filename}: {percentage:.1f}% ({speed / 1024:.1f} KB/s)")
                            last_log_time = current_time

                    # Log completion statistics
                    total_elapsed = time.time() - start_time
                    total_bytes = resume_offset + bytes_sent
                    avg_speed = total_bytes / (total_elapsed if total_elapsed > 0 else 1)

                    self.logger.info(
                        f"File {filename} sent successfully. Total: {total_bytes / 1024 / 1024:.2f} MB, Speed: {avg_speed / 1024 / 1024:.2f} MB/s")

                except ConnectionError as e:
                    # Handle connection errors during transfer
                    self.logger.error(f"Connection error while sending {filename}: {e}")
                except socket.timeout:
                    # Handle socket timeout during transfer
                    self.logger.error(f"Socket timeout while sending {filename}")
                except Exception as e:
                    # Handle other errors during transfer
                    self.logger.error(f"Error sending file {filename}: {e}")

        except json.JSONDecodeError:
            # Handle invalid JSON in client ready message
            self.logger.error(f"Received invalid JSON while waiting for ready message")
        except Exception as e:
            # Handle other unexpected errors
            self.logger.error(f"Error during file download for {filename}: {e}")

    def _calculate_file_hash(self, filepath):
        """Calculate SHA-256 hash of a file

        Args:
            filepath: Path to the file

        Returns:
            str: Hexadecimal digest of the file hash

        Reads the file in chunks to efficiently handle large files
        """
        hash_obj = hashlib.sha256()
        with open(filepath, 'rb') as f:
            while True:
                data = f.read(4096)
                if not data:
                    break
                hash_obj.update(data)
        return hash_obj.hexdigest()

    def _send_response(self, client_socket, response_data):
        """Send a JSON response to the client

        Args:
            client_socket: The client socket object
            response_data: Dictionary to be sent as JSON
        """
        response = json.dumps(response_data).encode('utf-8')
        client_socket.sendall(response)

    def handle_list(self, client_socket, client_id):
        """Handle request to list available files

        Args:
            client_socket: The client socket object
            client_id: Client identifier string for logging

        Collects metadata for all files in the storage directory
        and sends it to the client as a JSON response.
        Includes version history information for each file.
        """
        self.logger.info(f"List files request from {client_id}")
        files = []

        # Scan storage directory for files
        for filename in os.listdir(self.storage_dir):
            filepath = os.path.join(self.storage_dir, filename)
            if os.path.isfile(filepath):
                # Get file metadata
                modified_time = datetime.datetime.fromtimestamp(
                    os.path.getmtime(filepath)
                ).strftime('%Y-%m-%d %H:%M:%S')

                # Get version history for this file
                versions = self.get_version_history(filename)

                # Add file info to the list
                files.append({
                    'filename': filename,
                    'size': os.path.getsize(filepath),
                    'modified': modified_time,
                    'versions': versions
                })

        self.logger.info(f"Sent list of {len(files)} files to {client_id}")
        self.send_response(client_socket, {
            'status': 'success',
            'files': files
        })

    def send_response(self, client_socket, response_data):
        """Send a JSON response to the client

        Args:
            client_socket: The client socket object
            response_data: Dictionary to be sent as JSON
        """
        response = json.dumps(response_data).encode('utf-8')
        client_socket.sendall(response)

    def get_version_history(self, filename):
        """
        Get the version history for a specific file

        Args:
            filename: The name of the file

        Returns:
            list: List of version information dictionaries

        Scans the version history directory for previous versions
        of the specified file and collects their metadata.
        """
        # Extract base name and extension
        name, ext = os.path.splitext(filename)
        file_version_dir = os.path.join(self.version_dir, name)

        # Check if this file has any versions
        if not os.path.exists(file_version_dir):
            return []

        versions = []
        # Scan the file's version directory
        for version_file in os.listdir(file_version_dir):
            # Only include files that match the base name and extension
            if version_file.startswith(name) and version_file.endswith(ext):
                version_path = os.path.join(file_version_dir, version_file)
                version_time = datetime.datetime.fromtimestamp(
                    os.path.getmtime(version_path)
                ).strftime('%Y-%m-%d %H:%M:%S')

                # Add version info to the list
                versions.append({
                    'filename': version_file,
                    'size': os.path.getsize(version_path),
                    'modified': version_time
                })

        # Sort versions by filename (which includes timestamp) in descending order
        # This puts newest versions first
        versions.sort(key=lambda x: x['filename'], reverse=True)
        return versions


# Entry point for running the server directly
if __name__ == "__main__":
    server = FileServer()
    server.start()