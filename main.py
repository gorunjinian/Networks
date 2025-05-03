#!/usr/bin/env python3
"""
TCP File Transfer Application
Run this script to choose between starting a server or client.
"""

import sys
from server import FileServer


def print_header():
    """Print a header for the application"""
    print("\n" + "=" * 60)
    print("TCP File Transfer Application".center(60))
    print("=" * 60)


def main():
    """Main entry point for the application"""
    print_header()
    
    print("\nChoose an option:")
    print("1. Start Server")
    print("2. Start Client")
    print("3. Exit")
    
    while True:
        choice = input("\nEnter your choice (1-3): ")
        
        if choice == '1':
            print("\nStarting server...")
            server = FileServer()
            server.start()
            break
            
        elif choice == '2':
            print("\nStarting client...")
            # Import and use the main function from client.py
            from client import main as client_main
            client_main()
            break
            
        elif choice == '3':
            print("\nExiting...")
            sys.exit(0)
            
        else:
            print("Invalid choice. Please try again.")


if __name__ == '__main__':
    main()
