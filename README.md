# TCP File Transfer Application

This application implements a client-server file sharing system with the following features:

## Features

### A. Client-Server Architecture
- Server hosts shared files and allows multiple clients to connect
- Each client can upload, download, and list files
- Multiple clients are supported simultaneously using multithreading

### B. File Operations
- Upload Files: Clients can send files to the server for storage
- Download Files: Clients can request files from the server
- List Available Files: Clients can retrieve a list of files stored on the server

### C. Network Communication
- Uses TCP sockets to ensure reliable file transfers
- Implements a custom JSON-based request-response protocol
- Commands: UPLOAD, DOWNLOAD, LIST

### D. File Integrity Checking
- Uses SHA-256 hashing to verify file integrity after upload/download
- Prevents file corruption by comparing hashes before and after transfer

### E. File Duplicates Handling
- Three different strategies for handling duplicate files:
  1. **Overwrite**: Replace existing files with new uploads
  2. **Auto-rename**: Automatically rename new files (e.g., filename_v2.txt)
  3. **Version History**: Maintain a version history of previous files

### F. Logging System
- **Server-side logging**: Tracks client connections, file transfers, and errors
- **Client-side logging**: Records file transfers and error events
- Logs include timestamps and detailed event information
- Log rotation to prevent excessive log file sizes (5MB max with 5 backup files)

## Setup

1. Ensure you have Python 3.6+ installed on your system.
2. The application creates the following directories automatically:
   - `server_storage/` - Where the server stores uploaded files
   - `version_history/` - Where the server stores previous file versions
   - `server_logs/` - Where server logs are stored
   - `client_downloads/` - Where the client saves downloaded files
   - `client_logs/` - Where client logs are stored

## Usage

### Running the Server

```
python server.py
```

By default, the server runs on `0.0.0.0:5000` (all interfaces, port 5000).

### Running the Client

```
python client.py
```

By default, the client connects to `localhost:5000`.

### Client Menu Options

1. **Connect to server** - Establish a connection to the file server
2. **Upload file** - Send a file to the server
   - Choose how to handle duplicate files (overwrite, rename, version history)
3. **Download file** - Retrieve a file from the server
4. **List files** - View files available on the server
5. **View file versions** - See version history for a specific file
6. **Exit** - Close the connection and exit

## Protocol Details

The application uses a simple JSON-based protocol over TCP:

### Upload Protocol
1. Client sends: `{"command": "UPLOAD", "filename": "file.txt", "filesize": 1024, "hash": "sha256-hash", "handling_mode": "overwrite"}`
2. Server responds: `{"status": "ready", "filename": "file.txt", "is_duplicate": true, "handling_mode": "overwrite"}`
3. Client sends file data
4. Server verifies hash and responds: `{"status": "success", "message": "File uploaded successfully", "hash": "sha256-hash"}`

### Download Protocol
1. Client sends: `{"command": "DOWNLOAD", "filename": "file.txt"}`
2. Server responds: `{"status": "ready", "filename": "file.txt", "filesize": 1024, "hash": "sha256-hash"}`
3. Client sends: `{"status": "ready"}`
4. Server sends file data
5. Client verifies hash

### List Protocol
1. Client sends: `{"command": "LIST"}`
2. Server responds: `{"status": "success", "files": [{"filename": "file1.txt", "size": 1024, "modified": "2023-01-01 12:00:00", "versions": [...]}]}`

## Version History

The application maintains a history of file versions when using the "versioning" handling mode:

1. Each version is stored with a timestamp in the filename
2. Versions are organized in subdirectories by base filename
3. Users can view the version history through the client interface

## Logging System

Both client and server maintain detailed logs that include:

1. Connection events (client connects/disconnects)
2. File operations (uploads, downloads, file listings)
3. Error events (file not found, corrupted transfers)
4. Each log entry includes a timestamp, severity level, and detailed message

## Error Handling

The application handles various errors including:
- Connection errors
- File not found
- Corrupted file transfers (hash mismatch)
- Invalid commands
- File duplication conflicts

## Implementation Details

The implementation uses:
- Socket programming for network communication
- Multithreading for handling multiple clients
- JSON for structured message passing
- SHA-256 for file integrity verification
- Progress reporting during file transfers
- Logging with rotation for maintainable logs
