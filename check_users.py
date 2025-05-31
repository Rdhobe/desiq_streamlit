import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'desiq.settings')
django.setup()

from django.contrib.auth.models import User

def main():
    print("Users in database:")
    for user in User.objects.all():
        print(f"{user.id}: {user.first_name} {user.last_name} ({user.username})")

if __name__ == "__main__":
    main() 