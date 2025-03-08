from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import FileUpload, UserProfile


class CustomUserCreationForm(UserCreationForm):
    """Custom user registration form"""
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to form fields
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            # Create user profile
            UserProfile.objects.create(user=user, role='user')
        
        return user


class CustomAuthenticationForm(AuthenticationForm):
    """Custom login form"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to form fields
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['password'].widget.attrs.update({'class': 'form-control'})


class FileUploadForm(forms.ModelForm):
    """Form for file uploads"""
    HANDLING_CHOICES = [
        ('overwrite', 'Overwrite existing file'),
        ('versioning', 'Create new version'),
        ('rename', 'Auto-rename file')
    ]
    
    handling_mode = forms.ChoiceField(
        choices=HANDLING_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='overwrite',
        required=True
    )
    
    class Meta:
        model = FileUpload
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'})
        }


class UserRoleForm(forms.ModelForm):
    """Form for changing user roles"""
    class Meta:
        model = UserProfile
        fields = ['role']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'})
        }
