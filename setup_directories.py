#!/usr/bin/env python3
"""
Setup directories for the File Sharing System
"""

import os


def create_directory(dir_path):
    """Create directory if it doesn't exist"""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        print(f"Created directory: {dir_path}")
    else:
        print(f"Directory already exists: {dir_path}")


def main():
    """Create all required directories"""
    # File system directories
    create_directory('server_storage')
    create_directory('server_logs')
    create_directory('client_downloads')
    create_directory('client_logs')
    create_directory('version_history')

    # Web app directories
    create_directory('static/css')
    create_directory('static/js')
    create_directory('static/images')
    create_directory('media/uploads')
    create_directory('media/versions')

    # Django template directories
    create_directory('file_manager/templates/file_manager')
    create_directory('file_manager/templatetags')

    print("\nDirectory setup complete!")
    print("\nNext steps:")
    print("1. Run 'python manage.py makemigrations file_manager'")
    print("2. Run 'python manage.py migrate'")
    print("3. Run 'python manage.py createsuperuser'")
    print("4. Run 'python manage.py runserver' for the web interface")
    print("5. Or run 'python main.py' for the command line interface")


if __name__ == '__main__':
    main()