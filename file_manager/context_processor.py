def user_context(request):
    """Add user admin status to template context"""
    is_admin = False

    if request.user.is_authenticated:
        try:
            is_admin = request.user.userprofile.is_admin()
        except:
            is_admin = False

    return {
        'is_admin': is_admin
    }