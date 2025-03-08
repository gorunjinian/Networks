from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, Http404
from django.conf import settings
from django.db.models import Sum
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import os
import json
import hashlib
import mimetypes
from wsgiref.util import FileWrapper

from .models import FileUpload, FileVersion, SystemLogEntry, UserProfile
from .forms import CustomUserCreationForm, CustomAuthenticationForm, FileUploadForm, UserRoleForm


def index(request):
    """Home page view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'file_manager/index.html')


def register_view(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Log the registration
            SystemLogEntry.objects.create(
                level="INFO",
                action="AUTH",
                user=user,
                ip_address=get_client_ip(request),
                message=f"User {user.username} registered"
            )
            
            login(request, user)
            messages.success(request, "Registration successful.")
            return redirect("dashboard")
        messages.error(request, "Registration failed. Please check the form.")
    else:
        form = CustomUserCreationForm()
    
    return render(request, "file_manager/register.html", {"form": form})


def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == "POST":
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                # Log the login
                SystemLogEntry.objects.create(
                    level="INFO",
                    action="AUTH",
                    user=user,
                    ip_address=get_client_ip(request),
                    message=f"User {user.username} logged in"
                )
                
                messages.success(request, f"Welcome back, {username}!")
                return redirect("dashboard")
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = CustomAuthenticationForm()
    
    return render(request, "file_manager/login.html", {"form": form})


@login_required
def logout_view(request):
    """User logout view"""
    # Log the logout
    SystemLogEntry.objects.create(
        level="INFO",
        action="AUTH",
        user=request.user,
        ip_address=get_client_ip(request),
        message=f"User {request.user.username} logged out"
    )
    
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("login")


@login_required
def dashboard(request):
    """Main dashboard view"""
    # Get the user's files
    files = FileUpload.objects.filter(uploaded_by=request.user).order_by('-upload_date')
    
    # Paginate the files
    paginator = Paginator(files, 10)  # Show 10 files per page
    page_number = request.GET.get('page')
    files_page = paginator.get_page(page_number)
    
    # Calculate storage usage
    storage_used = files.aggregate(Sum('file_size'))['file_size__sum'] or 0
    
    # Check if user is admin
    is_admin = request.user.profile.is_admin()
    
    # If admin, get all users
    users = None
    if is_admin:
        users = UserProfile.objects.all().select_related('user')
    
    # Prepare upload form
    upload_form = FileUploadForm()
    
    context = {
        'files': files_page,
        'upload_form': upload_form,
        'storage_used': storage_used,
        'is_admin': is_admin,
        'users': users,
    }
    
    return render(request, 'file_manager/dashboard.html', context)


@login_required
def upload_file(request):
    """Handle file upload"""
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Extract file information
            uploaded_file = request.FILES['file']
            filename = uploaded_file.name
            handling_mode = request.POST.get('handling_mode', 'overwrite')
            
            # Check if file already exists
            existing_file = FileUpload.objects.filter(
                filename=filename,
                uploaded_by=request.user
            ).first()
            
            if existing_file and handling_mode == 'versioning':
                # Create a version of the existing file
                version_num = FileVersion.objects.filter(original_file=existing_file).count() + 1
                
                # Create a file version
                hash_obj = hashlib.sha256()
                for chunk in existing_file.file.chunks():
                    hash_obj.update(chunk)
                
                FileVersion.objects.create(
                    original_file=existing_file,
                    file=existing_file.file,
                    version=existing_file.version,
                    file_size=existing_file.file_size,
                    file_hash=hash_obj.hexdigest(),
                )
                
                # Update existing file with new version
                existing_file.file = uploaded_file
                existing_file.original_filename = filename
                existing_file.version += 1
                existing_file.status = 'completed'
                existing_file.save()
                
                file_upload = existing_file
                
                # Log the version update
                SystemLogEntry.objects.create(
                    level="INFO",
                    action="UPLOAD",
                    user=request.user,
                    ip_address=get_client_ip(request),
                    message=f"User {request.user.username} updated file {filename} to version {existing_file.version}",
                    file=file_upload
                )
                
            elif existing_file and handling_mode == 'rename':
                # Auto-rename the file
                name, ext = os.path.splitext(filename)
                version = 2
                while FileUpload.objects.filter(filename=f"{name}_v{version}{ext}", uploaded_by=request.user).exists():
                    version += 1
                
                new_filename = f"{name}_v{version}{ext}"
                
                # Create a new file
                file_upload = form.save(commit=False)
                file_upload.uploaded_by = request.user
                file_upload.filename = new_filename
                file_upload.original_filename = filename
                file_upload.status = 'completed'
                file_upload.save()
                
                # Log the upload
                SystemLogEntry.objects.create(
                    level="INFO",
                    action="UPLOAD",
                    user=request.user,
                    ip_address=get_client_ip(request),
                    message=f"User {request.user.username} uploaded file {new_filename} (renamed from {filename})",
                    file=file_upload
                )
                
            else:
                # Overwrite or no existing file
                if existing_file:
                    # Delete existing file
                    existing_file.delete()
                    
                # Create a new file
                file_upload = form.save(commit=False)
                file_upload.uploaded_by = request.user
                file_upload.filename = filename
                file_upload.original_filename = filename
                file_upload.status = 'completed'
                file_upload.save()
                
                # Log the upload
                SystemLogEntry.objects.create(
                    level="INFO",
                    action="UPLOAD",
                    user=request.user,
                    ip_address=get_client_ip(request),
                    message=f"User {request.user.username} uploaded file {filename}",
                    file=file_upload
                )
            
            messages.success(request, f"File {file_upload.filename} uploaded successfully.")
            return redirect('dashboard')
        
        messages.error(request, "Error uploading file. Please try again.")
    
    return redirect('dashboard')


@login_required
def download_file(request, file_id):
    """Handle file download"""
    file_upload = get_object_or_404(FileUpload, id=file_id)
    
    # Check if user has access to the file
    if not (file_upload.uploaded_by == request.user or request.user.profile.is_admin()):
        raise Http404
    
    # Log the download
    SystemLogEntry.objects.create(
        level="INFO",
        action="DOWNLOAD",
        user=request.user,
        ip_address=get_client_ip(request),
        message=f"User {request.user.username} downloaded file {file_upload.filename}",
        file=file_upload
    )
    
    # Serve the file
    file_path = file_upload.file.path
    file_wrapper = FileWrapper(open(file_path, 'rb'))
    file_mimetype = mimetypes.guess_type(file_path)[0]
    
    response = HttpResponse(file_wrapper, content_type=file_mimetype)
    response['Content-Disposition'] = f'attachment; filename="{file_upload.original_filename}"'
    response['Content-Length'] = os.path.getsize(file_path)
    
    return response


@login_required
def download_version(request, version_id):
    """Handle file version download"""
    version = get_object_or_404(FileVersion, id=version_id)
    
    # Check if user has access to the file
    if not (version.original_file.uploaded_by == request.user or request.user.profile.is_admin()):
        raise Http404
    
    # Log the download
    SystemLogEntry.objects.create(
        level="INFO",
        action="DOWNLOAD",
        user=request.user,
        ip_address=get_client_ip(request),
        message=f"User {request.user.username} downloaded version {version.version} of file {version.original_file.filename}",
        file=version.original_file
    )
    
    # Serve the file
    file_path = version.file.path
    file_wrapper = FileWrapper(open(file_path, 'rb'))
    file_mimetype = mimetypes.guess_type(file_path)[0]
    
    response = HttpResponse(file_wrapper, content_type=file_mimetype)
    response['Content-Disposition'] = f'attachment; filename="{version.original_file.original_filename}"'
    response['Content-Length'] = os.path.getsize(file_path)
    
    return response


@login_required
def file_detail(request, file_id):
    """View file details and versions"""
    file_upload = get_object_or_404(FileUpload, id=file_id)
    
    # Check if user has access to the file
    if not (file_upload.uploaded_by == request.user or request.user.profile.is_admin()):
        raise Http404
    
    # Get file versions
    versions = FileVersion.objects.filter(original_file=file_upload).order_by('-version')
    
    context = {
        'file': file_upload,
        'versions': versions,
    }
    
    return render(request, 'file_manager/file_detail.html', context)


@login_required
def delete_file(request, file_id):
    """Delete a file"""
    file_upload = get_object_or_404(FileUpload, id=file_id)
    
    # Check if user has permission to delete the file
    if not (file_upload.uploaded_by == request.user or request.user.profile.is_admin()):
        messages.error(request, "You don't have permission to delete this file.")
        return redirect('dashboard')
    
    filename = file_upload.filename
    
    # Log the deletion
    SystemLogEntry.objects.create(
        level="INFO",
        action="DELETE",
        user=request.user,
        ip_address=get_client_ip(request),
        message=f"User {request.user.username} deleted file {filename}"
    )
    
    # Delete the file
    file_upload.delete()
    
    messages.success(request, f"File {filename} deleted successfully.")
    return redirect('dashboard')


@login_required
def admin_logs(request):
    """View system logs (admin only)"""
    if not request.user.profile.is_admin():
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Get all logs
    logs = SystemLogEntry.objects.all().order_by('-timestamp')
    
    # Paginate the logs
    paginator = Paginator(logs, 20)  # Show 20 logs per page
    page_number = request.GET.get('page')
    logs_page = paginator.get_page(page_number)
    
    context = {
        'logs': logs_page,
    }
    
    return render(request, 'file_manager/admin_logs.html', context)


@login_required
def admin_users(request):
    """Manage users (admin only)"""
    if not request.user.profile.is_admin():
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Get all users
    users = UserProfile.objects.all().select_related('user')
    
    context = {
        'users': users,
    }
    
    return render(request, 'file_manager/admin_users.html', context)


@login_required
@require_POST
def change_user_role(request, user_id):
    """Change a user's role (admin only)"""
    if not request.user.profile.is_admin():
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('dashboard')
    
    user_profile = get_object_or_404(UserProfile, user_id=user_id)
    
    # Don't allow changing own role
    if user_profile.user == request.user:
        messages.error(request, "You cannot change your own role.")
        return redirect('admin_users')
    
    form = UserRoleForm(request.POST, instance=user_profile)
    if form.is_valid():
        form.save()
        
        # Log the role change
        SystemLogEntry.objects.create(
            level="INFO",
            action="OTHER",
            user=request.user,
            ip_address=get_client_ip(request),
            message=f"Admin {request.user.username} changed role of user {user_profile.user.username} to {user_profile.role}"
        )
        
        messages.success(request, f"Role for {user_profile.user.username} updated successfully.")
    else:
        messages.error(request, "Error updating user role.")
    
    return redirect('admin_users')


@login_required
@csrf_exempt
def update_progress(request):
    """Update file upload/download progress"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            filename = data.get('filename')
            progress = data.get('progress')
            speed = data.get('speed')
            action = data.get('action')
            
            # Send progress update to WebSocket
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'progress_{request.user.id}',
                {
                    'type': 'progress_update',
                    'filename': filename,
                    'progress': progress,
                    'speed': speed,
                    'action': action
                }
            )
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Only POST requests are allowed'})


def get_client_ip(request):
    """Helper function to get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
