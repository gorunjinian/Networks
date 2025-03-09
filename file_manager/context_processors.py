def user_context(request):
    """Add user admin status to template context"""
    is_admin = False

    if request.user.is_authenticated:
        try:
            # Consider both custom admin role and Django superuser status
            is_admin = request.user.profile.is_admin() or request.user.is_superuser
        except:
            # Fallback check for superuser in case of errors
            is_admin = request.user.is_superuser

    return {
        'is_admin': is_admin
    }