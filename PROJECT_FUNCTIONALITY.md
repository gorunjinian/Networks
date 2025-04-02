# Project Functionality Documentation

## 1. Overview

This project implements a client-server file sharing system using TCP sockets for communication. It allows users to upload, download, and list files stored on a central server. Key features include handling concurrent clients, file integrity verification using SHA-256 hashes, different modes for handling duplicate filenames (overwrite, rename, versioning), resumable downloads, and logging for both client and server operations. The project also includes components for a potential web interface using Django.

## 2. Architecture

The core system follows a client-server architecture:

*   **Server (`server.py`):** A multi-threaded TCP server that listens for client connections, manages file storage, handles client requests, and performs logging.
*   **Client (`client.py`):** A command-line TCP client that connects to the server, sends requests (upload, download, list), handles responses, manages local downloads, and performs logging.
*   **Launcher (`main.py`):** A simple script that provides a menu to start either the server or the client.
*   **Web Interface (Inferred):** Components like `manage.py`, `file_sharing_web/`, `file_manager/`, and `db.sqlite3` suggest a Django-based web application, likely providing a graphical interface for file operations and potentially user management.

## 3. Core Components Functionality

### 3.1. Server (`server.py`)

*   **Initialization:**
    *   Configures host, port, storage (`server_storage/`), logging (`server_logs/`), and version history (`server_storage/version_history/`) directories.
    *   Sets up logging to both console and a rotating file (`server.log`).
*   **Connection Handling:**
    *   Listens for incoming TCP connections on the configured host/port.
    *   Accepts connections and spawns a new thread (`handle_client`) for each client, allowing concurrent operations.
    *   Sets socket timeouts to prevent indefinite blocking.
*   **Request Processing:**
    *   Each client thread continuously listens for JSON messages from its client.
    *   Parses the `command` field from the JSON request.
*   **Command Implementation:**
    *   **`UPLOAD`:**
        1.  Receives `filename`, `filesize`, `hash`, and `handling_mode`.
        2.  Checks if the file exists in `server_storage`.
        3.  Based on `handling_mode`:
            *   `overwrite`: Prepares to replace the existing file.
            *   `rename`: Determines a new unique filename (e.g., `file_v2.txt`).
            *   `versioning`: Moves the existing file to the `version_history/` directory with a timestamp before proceeding.
        4.  Sends a `{'status': 'ready', ...}` response to the client, indicating the filename to be used.
        5.  Receives file data in chunks from the client.
        6.  Calculates the SHA-256 hash of the received data.
        7.  Compares the calculated hash with the client-provided hash.
        8.  Saves the file to `server_storage`.
        9.  Sends a final status response (`{'status': 'success'}` or `{'status': 'error'}`).
    *   **`DOWNLOAD`:**
        1.  Receives `filename` and optional `resume_offset`.
        2.  Checks if the file exists in `server_storage`.
        3.  Calculates the file's hash and gets its size.
        4.  Sends a `{'status': 'ready', 'filesize': ..., 'hash': ...}` response.
        5.  Reads the file from `server_storage` (starting from `resume_offset` if provided).
        6.  Sends the file data in chunks to the client.
    *   **`LIST`:**
        1.  Scans the `server_storage` directory.
        2.  Collects filenames, sizes, and modification times.
        3.  Sends the list back to the client in a JSON response `{'status': 'success', 'files': [...]}`.
*   **Logging:** Records server start/stop, connections, received commands, file operations (upload, download, rename, versioning), and errors.

### 3.2. Client (`client.py`)

*   **Initialization:**
    *   Configures server host/port, download directory (`client_downloads/`), and logging directory (`client_logs/`).
    *   Sets up logging to both console and a rotating file (`client.log`).
*   **Connection:**
    *   Establishes a TCP connection to the server.
    *   Handles connection errors (timeout, refusal) with basic retry attempts.
*   **Communication (`send_request`):**
    *   Takes a dictionary representing the request.
    *   Serializes it to JSON and sends it to the server.
    *   Receives the server's JSON response.
    *   Deserializes the JSON response and returns it.
    *   Includes retry logic for socket timeouts or connection errors during communication.
*   **Command-Line Interface (`main` function):**
    *   Provides a menu-driven interface:
        *   **Connect/Disconnect:** Manages the server connection.
        *   **Upload:**
            1.  Prompts user for the local file path and handling mode (`overwrite`, `rename`, `versioning`).
            2.  Checks if the local file exists.
            3.  Calculates the file's SHA-256 hash.
            4.  Calls `send_request` with the `UPLOAD` command and metadata.
            5.  If the server responds with `{'status': 'ready'}`, reads the local file and sends its content in chunks.
            6.  Waits for the final status response from the server.
        *   **Download:**
            1.  Prompts user for the filename to download.
            2.  Checks if a partial download exists in `client_downloads/` (e.g., `filename.part`). If so, determines the `resume_offset`.
            3.  Calls `send_request` with the `DOWNLOAD` command (including `resume_offset` if applicable).
            4.  If the server responds with `{'status': 'ready'}`, prepares to receive the file.
            5.  Receives file data in chunks, writing to a `.part` file.
            6.  If the transfer completes, calculates the hash of the downloaded data.
            7.  Compares the hash with the one provided by the server.
            8.  If hashes match, renames the `.part` file to the final filename.
            9.  Handles potential disconnections during download and attempts reconnection to resume.
        *   **List:**
            1.  Calls `send_request` with the `LIST` command.
            2.  Prints the list of files received from the server.
        *   **View Versions (Interface present, server logic might need specific command):** Provides an option, but the corresponding server command handling for retrieving specific versions wasn't fully detailed in the analyzed `server.py` snippets.
*   **Logging:** Records client actions, connection status, uploads, downloads, errors, and communication issues.

### 3.3. Launcher (`main.py`)

*   A simple script that imports `FileServer` and `FileClient`.
*   Displays a text menu asking the user whether to start the server (creates and runs `FileServer().start()`) or the client (calls the `main()` function from `client.py`).

## 4. Web Interface (Django) Functionality (`file_manager` app)

The Django web application provides a browser-based interface for file management and user administration. It runs separately from the core TCP server/client started via `main.py`.

*   **Technology Stack:**
    *   Backend: Django
    *   Database: SQLite (`db.sqlite3`)
    *   Real-time: Django Channels (WebSockets) for upload progress.
    *   Frontend: HTML Templates with Bootstrap 5, JavaScript.
*   **Storage:** Uses Django's `MEDIA_ROOT` setting, likely pointing to the `media/` directory at the project root, to store uploaded files (`media/uploads/`) and versions (`media/versions/`). **This is separate from the `server_storage/` directory used by the core TCP server.**
*   **Database Models (`models.py`):**
    *   `User`: Standard Django User model for authentication.
    *   `UserProfile`: Extends User to add roles ('admin', 'user'), track storage usage (`storage_used`), and enforce quotas (`storage_quota`, default 1GB).
    *   `FileUpload`: Stores metadata for files uploaded via the web interface (path in `MEDIA_ROOT`, original filename, size, SHA-256 hash, status, uploader User, current version number).
    *   `FileVersion`: Stores metadata for historical file versions created via the web interface's versioning feature (path in `MEDIA_ROOT`, hash, size, version number).
    *   `SystemLogEntry`: Database table used for logging web actions (AUTH, UPLOAD, DOWNLOAD, DELETE) including user, IP address, and associated file. **This is separate from the file-based logging of the core TCP server/client.**
*   **User Features:**
    *   **Authentication:** User registration, login, logout.
    *   **Dashboard:** Main view showing user's files (paginated), storage usage gauge, and upload form.
    *   **File Upload:** Upload files via a form. Options for handling duplicates ('overwrite', 'versioning' - rename seems intended but might be incomplete). Real-time progress bar powered by WebSockets.
    *   **File Download:** Download files owned by the user.
    *   **File Details:** View file metadata and list/download previous versions if available.
    *   **File Deletion:** Delete files owned by the user.
*   **Admin Features (Requires 'admin' role or superuser status):**
    *   **View All Files:** Admins can see files uploaded by all users on the dashboard.
    *   **System Logs:** View the `SystemLogEntry` table (web action logs).
    *   **User Management:** View all registered users and change their roles between 'user' and 'admin'.
*   **Real-time Progress:** Uses WebSockets (`ProgressConsumer`) to provide live feedback on file upload progress directly in the browser. The view handling the upload likely pushes updates through the channel layer.

## 5. Communication Protocol (Core TCP Client/Server)

*   **Transport:** TCP/IP Sockets.
*   **Format:** JSON for control messages (requests/responses).
*   **Commands:** `UPLOAD`, `DOWNLOAD`, `LIST`.
*   **File Transfer:** Raw byte stream over the socket after initial JSON negotiation.
*   **Integrity:** SHA-256 hash verification for both uploads and downloads. Client calculates hash before upload; server calculates hash after receiving upload. Server sends hash before download; client calculates hash after receiving download.

## 6. File Management (Core TCP Client/Server)

*   **Server Storage:** Files are stored in the `server_storage/` directory.
*   **Duplicate Handling:** Configurable via the `handling_mode` parameter during upload:
    *   `overwrite`: Replaces the existing file.
    *   `rename`: Keeps the existing file and saves the new one with a version suffix (e.g., `_v2`, `_v3`).
    *   `versioning`: Moves the current version of the file to `server_storage/version_history/` (with a timestamp in the name) before saving the new file under the original name.
*   **Client Downloads:** Files are saved in the `client_downloads/` directory. Partial downloads are stored with a `.part` extension until complete and verified.

## 7. Key Features Summary

*   **Dual Interfaces:** Offers both a command-line interface (via `client.py`) and a graphical web interface (via Django) for file operations.
*   **Core TCP System:**
    *   **Client-Server Model:** Centralized file storage (`server_storage/`) on the server, accessible by multiple CLI clients.
    *   **Concurrency:** Server handles multiple CLI clients simultaneously using threading.
    *   **File Integrity:** SHA-256 checksums ensure files are not corrupted during TCP transfer.
    *   **Duplicate Handling:** Flexible options (overwrite, rename, versioning) for CLI uploads.
    *   **Resumable Downloads:** CLI client can resume interrupted downloads.
    *   **File Logging:** Detailed text logs (`server_logs/`, `client_logs/`) for troubleshooting and monitoring TCP operations.
*   **Web Interface System (Django):**
    *   **User Authentication:** Manages users, roles, and sessions.
    *   **Web-based File Management:** Upload, download, list, delete, and version files via the browser, using separate storage (`media/`).
    *   **Real-time Feedback:** WebSocket-based upload progress bars.
    *   **Administration:** Tools for viewing system logs (web actions) and managing user roles.
    *   **Database Logging:** Logs web actions to a database table.

**Note:** The core TCP client/server and the Django web interface appear to operate as two separate systems sharing similar concepts (file transfer, versioning) but using different storage locations, logging mechanisms, and lacking direct integration in the analyzed code. A user uploading via the CLI would likely not see the file in the web UI, and vice-versa. 