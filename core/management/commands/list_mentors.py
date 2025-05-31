from django.core.management.base import BaseCommand
from core.models import Mentor

class Command(BaseCommand):
    help = 'List all mentors by type'

    def handle(self, *args, **kwargs):
        total_mentors = Mentor.objects.count()
        self.stdout.write(f"Total mentors: {total_mentors}")
        
        # Get all mentor types from the choices defined in the model
        mentor_types = [type_code for type_code, _ in Mentor.MENTOR_TYPES]
        
        for mentor_type in mentor_types:
            mentors = Mentor.objects.filter(type=mentor_type)
            if mentors.exists():
                # Get the display name from the choices
                display_type = dict(Mentor.MENTOR_TYPES)[mentor_type]
                self.stdout.write(f"\n{display_type} ({mentors.count()}):")
                
                # List mentors of this type
                for mentor in mentors:
                    premium_status = "Premium" if mentor.is_premium else "Free"
                    self.stdout.write(f"- {mentor.name} ({premium_status}): {mentor.expertise}") 