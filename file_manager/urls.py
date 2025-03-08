from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('upload/', views.upload_file, name='upload_file'),
    path('download/<int:file_id>/', views.download_file, name='download_file'),
    path('download-version/<int:version_id>/', views.download_version, name='download_version'),
    path('file/<int:file_id>/', views.file_detail, name='file_detail'),
    path('delete/<int:file_id>/', views.delete_file, name='delete_file'),
    path('admin/logs/', views.admin_logs, name='admin_logs'),
    path('admin/users/', views.admin_users, name='admin_users'),
    path('admin/users/change-role/<int:user_id>/', views.change_user_role, name='change_user_role'),
    path('update-progress/', views.update_progress, name='update_progress'),
]
