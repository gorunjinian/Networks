from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from file_manager.models import UserProfile


class Command(BaseCommand):
    help = 'Create user profiles for users that do not have one'

    def handle(self, *args, **options):
        users_without_profile = []

        for user in User.objects.all():
            try:
                # Try to access the profile
                profile = user.userprofile
            except User.userprofile.RelatedObjectDoesNotExist:
                # Create profile if it doesn't exist
                users_without_profile.append(user)
                UserProfile.objects.create(user=user)

        if users_without_profile:
            self.stdout.write(self.style.SUCCESS(f'Created profiles for {len(users_without_profile)} users'))
        else:
            self.stdout.write(self.style.SUCCESS('All users already have profiles'))