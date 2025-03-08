# TCP File Sharing Application

## Overview

This application implements a robust client-server file sharing system with a web interface. It allows users to securely transfer files over TCP/IP networks with integrity verification, version control, and real-time progress monitoring.

## Table of Contents

1. [Features](#features)
2. [Architecture](#architecture)
3. [Setup and Installation](#setup-and-installation)
4. [Usage](#usage)
   - [Command-Line Interface](#command-line-interface)
   - [Web Interface](#web-interface)
5. [Protocol Details](#protocol-details)
6. [File Management](#file-management)
7. [Security Features](#security-features)
8. [Logging System](#logging-system)
9. [Error Handling & Recovery](#error-handling--recovery)
10. [Implementation Details](#implementation-details)
11. [Troubleshooting](#troubleshooting)
12. [Performance Considerations](#performance-considerations)
13. [Future Enhancements](#future-enhancements)

## Features

### A. Client-Server Architecture
- Multi-threaded server that supports concurrent client connections
- Socket timeouts and connection retry mechanisms for reliability
- Command-line and web interfaces for user interaction

### B. File Operations
- **Upload Files**: With progress monitoring and integrity verification
- **Download Files**: With resumable transfers if interrupted
- **List Available Files**: With detailed metadata
- **Version History**: Track and retrieve previous versions of files

### C. Network Communication
- TCP sockets with timeout handling for reliable data transfer
- Resilient against network interruptions with auto-reconnect
- Custom JSON-based request-response protocol with error handling
- WebSocket integration for real-time progress updates

### D. File Integrity Checking
- SHA-256 hashing to verify file integrity before and after transfer
- Automatic corruption detection and cleanup of incomplete transfers
- Hash verification for both uploads and downloads

### E. File Duplicates Handling
- **Overwrite**: Replace existing files with new uploads
- **Auto-rename**: Automatically append version numbers (e.g., filename_v2.txt)
- **Version History**: Maintain an archive of previous file versions

### F. Logging System
- Comprehensive server-side and client-side logging
- Detailed error tracking with timestamps and context information
- Log rotation to manage log file sizes (5MB with 5 backup files)

### G. Web Interface
- User authentication with role-based access control
- Real-time progress monitoring via WebSockets
- Responsive design for desktop and mobile devices
- Secure session management

## Architecture

The application consists of the following components:

### Core Components
- **Server (`server.py`)**: Handles client connections, file operations, and version management
- **Client (`client.py`)**: Provides command-line interface for connecting to the server and managing files
- **Main (`main.py`)**: Entry point that allows choosing between server and client mode

### Web Interface Components
- **Django Framework**: Provides the web server and MVC architecture
- **Channels**: Handles WebSocket connections for real-time updates
- **ASGI Server**: Routes both HTTP and WebSocket traffic
- **File Manager App**: Implements file operations and user authentication

### Directory Structure
```
TCP-File-Sharing/
├── server.py                # Server implementation
├── client.py                # Command-line client
├── main.py                  # Application entry point
├── server_storage/          # Uploaded files storage
├── version_history/         # Previous file versions
├── server_logs/             # Server log files
├── client_logs/             # Client log files
├── client_downloads/        # Downloaded files
├── file_sharing_web/        # Django project directory
│   ├── settings.py          # Django settings
│   ├── urls.py              # Main URL routing
│   ├── asgi.py              # ASGI configuration
│   └── wsgi.py              # WSGI configuration
└── file_manager/            # Django app for file management
    ├── views.py             # HTTP request handlers
    ├── consumers.py         # WebSocket consumers
    ├── models.py            # Database models
    ├── urls.py              # App URL routing
    ├── routing.py           # WebSocket routing
    └── templates/           # HTML templates
```

## Setup and Installation

### Prerequisites
- Python 3.6 or higher
- pip (Python package manager)

### Installation Steps

1. **Clone or download the repository**
   ```
   git clone <repository-url>
   cd tcp-file-sharing
   ```

2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

3. **Configure the application (optional)**
   - Edit `server.py` to change default host/port (default: 0.0.0.0:5000)
   - Edit `client.py` to change default connection (default: localhost:5000)
   - Edit `file_sharing_web/settings.py` for Django configuration

4. **Set up the Django web interface**
   ```
   python manage.py makemigrations file_manager
   python manage.py migrate
   python manage.py createsuperuser  # Create admin user
   ```

### Directory Setup
The application automatically creates the following directories if they don't exist:
- `server_storage/` - Storage location for uploaded files
- `version_history/` - Archive of previous file versions
- `server_logs/` - Server log files with rotation
- `client_downloads/` - Default location for downloaded files
- `client_logs/` - Client-side logging

## Usage

### Command-Line Interface

#### Running the Server
```
python main.py
# Select option 1 to start the server
```
Or directly:
```
python server.py
```

#### Running the Client
```
python main.py
# Select option 2 to start the client
```
Or directly:
```
python client.py
```

#### Client Menu Options
1. **Connect to server** - Establish connection (with retry capability)
2. **Upload file** - Send a file with options for handling duplicates
3. **Download file** - Retrieve a file (with resume capability if interrupted)
4. **List files** - View available files and metadata
5. **View file versions** - See version history for specific files
6. **Exit** - Gracefully close connection and exit

### Web Interface

#### Starting the Web Server
```
python manage.py runserver
```

#### Accessing the Web Interface
Open a browser and navigate to `http://localhost:8000/`

#### Web Interface Features
- **User Authentication**: Register, login, and manage your account
- **File Upload**: Drag-and-drop or file browser with progress monitoring
- **File Download**: Download files with integrity verification
- **File Management**: List, search, and manage your files
- **Version History**: View and restore previous versions

## Protocol Details

The application uses a custom JSON-based protocol over TCP:

### Upload Protocol
1. Client sends: 
   ```json
   {
     "command": "UPLOAD", 
     "filename": "file.txt", 
     "filesize": 1024, 
     "hash": "sha256-hash", 
     "handling_mode": "overwrite"
   }
   ```
2. Server responds: 
   ```json
   {
     "status": "ready", 
     "filename": "file.txt", 
     "is_duplicate": true, 
     "handling_mode": "overwrite"
   }
   ```
3. Client sends file data in chunks
4. Server verifies hash and responds: 
   ```json
   {
     "status": "success", 
     "message": "File uploaded successfully", 
     "hash": "sha256-hash"
   }
   ```

### Download Protocol
1. Client sends: 
   ```json
   {
     "command": "DOWNLOAD", 
     "filename": "file.txt"
   }
   ```
   For resuming interrupted downloads:
   ```json
   {
     "command": "DOWNLOAD", 
     "filename": "file.txt", 
     "resume_offset": 1024
   }
   ```

2. Server responds: 
   ```json
   {
     "status": "ready", 
     "filesize": 1024, 
     "hash": "sha256-hash",
     "resuming_from": 1024  // Only for resumed downloads
   }
   ```
3. Client sends: 
   ```json
   {
     "status": "ready"
   }
   ```
4. Server sends file data (from offset if resuming)
5. Client verifies hash after receiving complete file

### List Protocol
1. Client sends: 
   ```json
   {
     "command": "LIST"
   }
   ```
2. Server responds: 
   ```json
   {
     "status": "success", 
     "files": [
       {
         "filename": "file1.txt", 
         "size": 1024, 
         "modified": "2023-01-01 12:00:00", 
         "versions": [...]
       },
       ...
     ]
   }
   ```

## File Management

### Storage Structure
- Main files are stored in `server_storage/`
- Version history is maintained in `version_history/<base_filename>/`
- Downloaded files are saved to `client_downloads/`

### Version History
The application maintains meticulous versioning when using the "versioning" mode:
1. Original files remain in `server_storage/`
2. Previous versions are stored in `version_history/<base_filename>/`
3. Version naming follows the pattern: `filename_YYYYMMDD_HHMMSS.ext`
4. Full metadata is maintained for all versions

### File Integrity
- All file transfers are verified using SHA-256 hash
- The hash is calculated before sending and verified after receiving
- Corrupted transfers are automatically detected and rejected
- Partial files from interrupted transfers are removed

## Security Features

### Network Security
- Session-based authentication for the web interface
- CSRF protection for web forms
- Content Security Policy headers
- XSS protection

### Data Security
- File integrity verification using SHA-256
- Version history for data recovery
- Secure file handling with proper cleanup

### Access Control
- Role-based permissions in the web interface
- User authentication required for file operations
- Admin interface for user management

## Logging System

Both client and server maintain detailed logs with the following characteristics:

### Log Categories
- **INFO**: Normal operations (connections, file transfers)
- **WARNING**: Non-critical issues (duplicate files, retries)
- **ERROR**: Critical issues (connection failures, file corruption)
- **DEBUG**: Detailed debugging information

### Log Structure
Each log entry includes:
- Timestamp (ISO 8601 format)
- Log level
- Component identifier
- Detailed message with context
- Exception details (for errors)

### Log Management
- Log rotation: 5MB maximum file size
- Backup count: 5 files
- Separate logs for server and client
- Detailed network and file operation tracking

## Error Handling & Recovery

The application includes comprehensive error handling mechanisms:

### Network Errors
- Socket timeouts with configurable values
- Connection retry logic with exponential backoff
- Graceful disconnection handling

### File Transfer Errors
- Resumable downloads for interrupted transfers
- Automatic cleanup of partial/corrupted files
- Hash verification to ensure data integrity

### WebSocket Error Handling
- Connection authentication validation
- Ping-pong mechanism for connection health checks
- Proper error reporting to the client interface

### User Input Validation
- Comprehensive validation of all user inputs
- Helpful error messages for invalid inputs
- Protection against malformed requests

## Implementation Details

### Technology Stack
- **Core**: Python 3.6+, TCP Sockets
- **Web Framework**: Django
- **WebSockets**: Django Channels with ASGI
- **Data Format**: JSON for communication
- **Hashing**: SHA-256 for file integrity
- **Concurrency**: Threading for multi-client support

### Performance Optimizations
- Chunked file transfers to minimize memory usage
- Progress monitoring with minimal overhead
- Efficient file hash calculation
- Optimized database queries in the web interface

### Resilience Mechanisms
- Timeout handling for network operations
- Retries for transient errors
- Resource cleanup in error scenarios
- Exception handling at all levels

## Troubleshooting

### Common Issues and Solutions

#### Connection Problems
- **Issue**: Unable to connect to server
  - **Solution**: Verify server is running and check firewall settings
  - **Solution**: Ensure correct host/port configuration
  - **Solution**: Check for network connectivity issues

#### File Transfer Issues
- **Issue**: File upload fails
  - **Solution**: Check available disk space on server
  - **Solution**: Verify file permissions
  - **Solution**: Try a different handling mode for duplicates

- **Issue**: Download interruptions
  - **Solution**: The application will automatically attempt to resume
  - **Solution**: If resume fails, restart the download

#### Web Interface Issues
- **Issue**: WebSocket connection fails
  - **Solution**: Ensure ASGI server is running
  - **Solution**: Check browser console for error messages
  - **Solution**: Verify user authentication

#### Permission Issues
- **Issue**: Access denied errors
  - **Solution**: Check user account permissions
  - **Solution**: Verify file ownership and access rights

### Logging for Troubleshooting
- Check `server_logs/` and `client_logs/` for detailed error information
- Enable DEBUG logging in Django settings for more verbose web interface logs

## Performance Considerations

### Optimizing for Large Files
- The application uses chunked transfers to minimize memory usage
- For very large files (>1GB), consider adjusting the chunk size
- File hash calculation is optimized to minimize memory footprint

### Network Considerations
- TCP socket buffer sizes are optimized for typical file transfers
- Connection timeouts are configurable based on network reliability
- Progress reporting frequency is balanced for performance

### Concurrent Operations
- The server can handle multiple clients simultaneously
- Each client connection runs in a separate thread
- Database operations are optimized for concurrent access

## Future Enhancements

Potential future improvements could include:

1. End-to-end encryption for enhanced security
2. Differential sync for bandwidth optimization
3. Directory/folder synchronization
4. Mobile application for remote access
5. Cloud storage integration
6. Compression options for large files
7. More advanced search and filtering
8. Collaborative features such as file sharing and permissions

---

This project provides a robust and flexible file sharing solution suitable for both personal and small-team use. The combination of a reliable TCP protocol, comprehensive error handling, and multiple interface options makes it adaptable to various usage scenarios.
