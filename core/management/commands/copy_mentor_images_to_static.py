from django.core.management.base import BaseCommand
from core.models import Mentor
import os
import shutil
from django.conf import settings

class Command(BaseCommand):
    help = 'Copy mentor images from media to static directory'

    def handle(self, *args, **kwargs):
        mentors = Mentor.objects.all()
        
        # Ensure directory exists for mentor images
        target_dir = os.path.join(settings.STATICFILES_DIRS[0], "img/mentor_images")
        os.makedirs(target_dir, exist_ok=True)
        
        # Count variables for reporting
        found_count = 0
        not_found_count = 0
        
        self.stdout.write(self.style.SUCCESS(f'Starting to copy mentor images to static directory...'))
        
        for mentor in mentors:
            if mentor.image:
                # Check if the image is already using the new format
                if os.path.exists(os.path.join(target_dir, mentor.image)):
                    self.stdout.write(self.style.SUCCESS(f'Image already exists for mentor {mentor.name}: {mentor.image}'))
                    found_count += 1
                    continue
                
                # Look for the image in the media directory
                media_path = os.path.join(settings.MEDIA_ROOT, 'mentor_images', mentor.image)
                if os.path.exists(media_path):
                    # Copy the file to the static directory
                    target_path = os.path.join(target_dir, os.path.basename(mentor.image))
                    shutil.copyfile(media_path, target_path)
                    self.stdout.write(self.style.SUCCESS(f'Copied image for mentor {mentor.name}: {mentor.image}'))
                    found_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f'Image not found for mentor {mentor.name}: {media_path}'))
                    not_found_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Finished copying mentor images to static directory'))
        self.stdout.write(f'Images found and copied: {found_count}')
        self.stdout.write(f'Images not found: {not_found_count}') 