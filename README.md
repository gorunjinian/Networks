# TCP Command-Line File Sharing Application

## Overview

This application implements a robust command-line client-server file sharing system using TCP/IP sockets. It allows users to securely transfer files over a network with integrity verification using SHA-256 hashes, options for handling duplicate files, resumable downloads, and detailed logging.

## Table of Contents

1.  [Features](#features)
2.  [Architecture](#architecture)
3.  [Setup and Installation](#setup-and-installation)
4.  [Usage](#usage)
5.  [Protocol Details](#protocol-details)
6.  [File Management](#file-management)
7.  [Logging System](#logging-system)
8.  [Error Handling & Recovery](#error-handling--recovery)

## Features

*   **Client-Server Architecture**: Multi-threaded server supporting concurrent client connections.
*   **TCP Communication**: Reliable file transfer over TCP sockets with timeout handling.
*   **File Operations**:
    *   Upload files with integrity checks.
    *   Download files with resumable transfers.
    *   List available files on the server.
*   **File Integrity**: SHA-256 hashing ensures files are not corrupted during transfer.
*   **Duplicate File Handling**: Options for `overwrite`, `rename` (e.g., `file_v2.txt`), or `versioning` (archiving previous versions).
*   **Logging**: Comprehensive server-side and client-side logging to files and console. Includes log rotation.
*   **Command-Line Interface**: Menu-driven client for easy interaction.

## Architecture

The application consists of the following core components:

*   **Server (`server.py`)**: Handles client connections, processes commands (`UPLOAD`, `DOWNLOAD`, `LIST`), manages file storage (`server_storage/`), and handles versioning (`version_history/`).
*   **Client (`client.py`)**: Provides a command-line interface (CLI) for connecting to the server, sending commands, and managing local downloads (`client_downloads/`).
*   **Main (`main.py`)**: A simple entry point script that allows choosing whether to start the server or the client.

### Directory Structure

```
TCP-File-Sharing/
├── server.py           # Server implementation
├── client.py           # Command-line client
├── main.py             # Application entry point
├── server_storage/     # Server-side storage for uploaded files
│   └── version_history/ # Archive of previous file versions (when versioning mode is used)
├── server_logs/        # Server log files
├── client_downloads/   # Default client download location
├── client_logs/        # Client log files
├── requirements.txt    # (Currently empty - no external packages needed)
└── README.md           # This file
```

## Setup and Installation

### Prerequisites

*   Python 3.6 or higher

### Installation Steps

1.  **Clone or download the repository:**
    ```bash
    git clone <repository-url>
    cd TCP-File-Sharing
    ```
    (Replace `<repository-url>` with the actual URL of your Git repository if applicable)

2.  **Dependencies:**
    This project currently uses only standard Python libraries. No external packages need to be installed via `pip`. The `requirements.txt` file is included but is empty.

### Directory Setup

The application automatically creates the following directories upon first run if they don't exist:

*   `server_storage/`
*   `server_storage/version_history/`
*   `server_logs/`
*   `client_downloads/`
*   `client_logs/`

### Configuration (Optional)

*   Edit `server.py` to change the default host/port for the server (default: `0.0.0.0:5000`).
*   Edit `client.py` to change the default server host/port the client tries to connect to (default: `localhost:5000`).

## Usage

You can run the server and client using the `main.py` script or by running `server.py` and `client.py` directly.

### Using the Launcher (`main.py`)

1.  Open your terminal or command prompt in the project directory.
2.  Run the launcher:
    ```bash
    python main.py
    ```
3.  Follow the on-screen menu:
    *   Select `1` to start the server.
    *   Select `2` to start the client.
    *   Select `3` to exit.

### Running Server Directly

```bash
python server.py
```
The server will start listening on the configured host and port (default: `0.0.0.0:5000`).

### Running Client Directly

```bash
python client.py
```
The client will start and present a menu for interacting with the server.

### Client Menu Options

1.  **Connect to server**: Establish or re-establish a connection to the server.
2.  **Upload file**: Select a local file to upload. You will be prompted for how to handle duplicates if the file exists on the server (`overwrite`, `rename`, `versioning`).
3.  **Download file**: Enter the name of a file on the server to download. Downloads are resumable if interrupted.
4.  **List files**: View the list of files currently stored on the server.
5.  **View file versions**: (Note: This client option might exist, but server logic for retrieving specific historical versions may need further implementation based on `PROJECT_FUNCTIONALITY.md`). Check server logs for archived filenames if needed.
6.  **Disconnect from server**: Close the current connection.
7.  **Exit**: Disconnect and close the client application.

## Protocol Details

The application uses a custom JSON-based protocol over TCP for control messages, followed by raw byte streams for file data.

### Upload Protocol Example

1.  Client sends `UPLOAD` command with metadata (filename, size, hash, handling\_mode).
2.  Server checks for duplicates, potentially archives/renames, and responds with `status: ready` and the final filename.
3.  Client sends file data in chunks.
4.  Server receives data, verifies hash, saves the file, and responds with `status: success` or `status: error`.

### Download Protocol Example

1.  Client sends `DOWNLOAD` command with filename (and optionally `resume_offset` if resuming).
2.  Server checks if file exists, gets size/hash, and responds with `status: ready`.
3.  Server sends file data in chunks (starting from offset if specified).
4.  Client receives data, saves to a `.part` file, verifies hash upon completion, and renames the file.

## File Management

*   **Server Storage**: Files are stored in the `server_storage/` directory.
*   **Duplicate Handling**: Controlled by the `handling_mode` parameter during upload (`overwrite`, `rename`, `versioning`).
    *   `versioning`: Moves the existing file to a timestamped file within `server_storage/version_history/<original_filename>/`.
*   **Client Downloads**: Files are saved in `client_downloads/`. Partial downloads use a `.part` extension until verified.

## Logging System

*   Separate log files for server (`server_logs/server.log`) and client (`client_logs/client.log`).
*   Logs include timestamps, severity levels, and informative messages about connections, commands, file operations, and errors.
*   Log rotation is enabled (default: 5MB per file, 5 backup files).
*   Logs are also output to the console.

## Error Handling & Recovery

*   **Timeouts**: Socket timeouts are used to prevent indefinite blocking during connection and data transfer.
*   **Connection Errors**: Client attempts to reconnect if communication fails during operations.
*   **File Integrity**: SHA-256 checks prevent corrupted files from being saved. Partial downloads are cleaned up or resumed.
*   **Graceful Shutdown**: Server and client attempt to close connections cleanly on exit (e.g., Ctrl+C).

---
