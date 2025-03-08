from django.db import models
from django.contrib.auth.models import User
import os
import hashlib
from django.utils import timezone

# Create your models here.
class FileUpload(models.Model):
    """Model to store uploaded files and their metadata"""
    FILE_STATUS_CHOICES = (
        ('uploading', 'Uploading'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    file = models.FileField(upload_to='uploads/')
    filename = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    file_hash = models.CharField(max_length=64)  # SHA-256 hash
    upload_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=FILE_STATUS_CHOICES, default='uploading')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploads')
    version = models.IntegerField(default=1)
    
    def save(self, *args, **kwargs):
        # If this is a new file (no ID yet), calculate its hash
        if not self.id and self.file:
            self.file_size = self.file.size
            
            # Calculate file hash
            hash_obj = hashlib.sha256()
            for chunk in self.file.chunks():
                hash_obj.update(chunk)
            self.file_hash = hash_obj.hexdigest()
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.filename} (v{self.version})"
    
    class Meta:
        ordering = ['-upload_date']


class FileVersion(models.Model):
    """Model to store previous versions of files"""
    original_file = models.ForeignKey(FileUpload, on_delete=models.CASCADE, related_name='versions')
    file = models.FileField(upload_to='versions/')
    version = models.IntegerField()
    file_size = models.BigIntegerField()
    file_hash = models.CharField(max_length=64)
    upload_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.original_file.filename} (v{self.version})"
    
    class Meta:
        ordering = ['-version']


class SystemLogEntry(models.Model):
    """Model to store system logs"""
    LOG_LEVEL_CHOICES = (
        ('INFO', 'Information'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
    )
    
    ACTION_CHOICES = (
        ('UPLOAD', 'Upload'),
        ('DOWNLOAD', 'Download'),
        ('DELETE', 'Delete'),
        ('AUTH', 'Authentication'),
        ('OTHER', 'Other'),
    )
    
    timestamp = models.DateTimeField(default=timezone.now)
    level = models.CharField(max_length=10, choices=LOG_LEVEL_CHOICES)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='log_entries')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    message = models.TextField()
    file = models.ForeignKey(FileUpload, on_delete=models.SET_NULL, null=True, blank=True, related_name='log_entries')
    
    def __str__(self):
        return f"{self.timestamp} - {self.level} - {self.action} - {self.user}"
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'System Log Entry'
        verbose_name_plural = 'System Log Entries'


class UserProfile(models.Model):
    """Extension of the User model to store additional user information"""
    ROLE_CHOICES = (
        ('admin', 'Administrator'),
        ('user', 'Regular User'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    storage_used = models.BigIntegerField(default=0)
    
    def __str__(self):
        return f"{self.user.username} ({self.role})"
    
    def is_admin(self):
        return self.role == 'admin'
