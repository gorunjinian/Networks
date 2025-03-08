from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from file_manager.models import UserProfile

class Command(BaseCommand):
    help = 'Creates user profiles for any users that do not have one'

    def handle(self, *args, **options):
        users_without_profiles = 0
        
        for user in User.objects.all():
            try:
                # Try to access the profile to see if it exists
                profile = user.profile
                self.stdout.write(f"User {user.username} already has a profile")
            except User.profile.RelatedObjectDoesNotExist:
                # Create a profile if it doesn't exist
                UserProfile.objects.create(user=user)
                users_without_profiles += 1
                self.stdout.write(self.style.SUCCESS(f"Created profile for user {user.username}"))
        
        if users_without_profiles:
            self.stdout.write(self.style.SUCCESS(f"Created {users_without_profiles} user profiles"))
        else:
            self.stdout.write(self.style.SUCCESS("All users already have profiles"))
