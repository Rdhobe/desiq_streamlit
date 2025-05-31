from django.core.management.base import BaseCommand
from core.models import Mentor
import os
import shutil
from django.conf import settings

class Command(BaseCommand):
    help = 'Add mentors to the database'

    def handle(self, *args, **kwargs):
        mentors_data = {
            "career_coach": [
                {
                    "name": "Michael Stevens",
                    "description": "Career coach with 15+ years experience in tech industry transitions and leadership development.",
                    "expertise": "Career transitions, Leadership development, Tech industry coaching",
                    "is_premium": False,
                    "image_path": "img/mentors/career_coach_regular.svg"
                },
                {
                    "name": "Sarah Johnson",
                    "description": "Executive coach specializing in helping professionals advance to senior management roles.",
                    "expertise": "Executive coaching, Promotion strategies, Personal branding",
                    "is_premium": True,
                    "image_path": "img/mentors/career_coach_premium.svg"
                }
            ],
            "financial_advisor": [
                {
                    "name": "Robert Chen",
                    "description": "Financial advisor with expertise in personal investment strategies and retirement planning.",
                    "expertise": "Investment planning, Retirement strategies, Tax optimization",
                    "is_premium": False,
                    "image_path": "img/mentors/financial_advisor_regular.svg"
                },
                {
                    "name": "Priya Sharma",
                    "description": "Certified financial planner specializing in debt management and building wealth for young professionals.",
                    "expertise": "Debt management, Wealth building, Financial literacy",
                    "is_premium": True,
                    "image_path": "img/mentors/financial_advisor_premium.svg"
                }
            ],
            "relationship_counselor": [
                {
                    "name": "Dr. Emily Williams",
                    "description": "Relationship counselor with a focus on communication strategies and conflict resolution.",
                    "expertise": "Communication, Conflict resolution, Building trust",
                    "is_premium": False,
                    "image_path": "img/mentors/relationship_counselor_regular.svg"
                },
                {
                    "name": "James Rodriguez",
                    "description": "Couples therapist specializing in helping partners reconnect and strengthen their relationships.",
                    "expertise": "Couples therapy, Emotional intimacy, Relationship rebuilding",
                    "is_premium": True,
                    "image_path": "img/mentors/relationship_counselor_premium.svg"
                }
            ],
            "time_management_expert": [
                {
                    "name": "Alex Morgan",
                    "description": "Productivity coach who helps professionals optimize their workflow and reduce stress.",
                    "expertise": "Productivity systems, Work-life balance, Stress management",
                    "is_premium": False,
                    "image_path": "img/mentors/time_management_expert_regular.svg"
                },
                {
                    "name": "Tanya Liu",
                    "description": "Time management specialist for entrepreneurs and busy executives.",
                    "expertise": "Calendar optimization, Delegation strategies, Focus techniques",
                    "is_premium": True,
                    "image_path": "img/mentors/time_management_expert_premium.svg"
                }
            ],
            "educational_consultant": [
                {
                    "name": "Dr. David Park",
                    "description": "Educational consultant with expertise in higher education planning and academic success strategies.",
                    "expertise": "College planning, Academic success, Learning strategies",
                    "is_premium": False,
                    "image_path": "img/mentors/educational_consultant_regular.svg"
                },
                {
                    "name": "Maria Gonzalez",
                    "description": "Education specialist focusing on alternative learning paths and career development for students.",
                    "expertise": "Alternative education, Career guidance, Skill development",
                    "is_premium": True,
                    "image_path": "img/mentors/educational_consultant_premium.svg"
                }
            ],
            "health_wellness_coach": [
                {
                    "name": "Thomas Wright",
                    "description": "Wellness coach specializing in holistic health approaches and sustainable lifestyle changes.",
                    "expertise": "Holistic wellness, Habit formation, Stress reduction",
                    "is_premium": False,
                    "image_path": "img/mentors/health_wellness_coach_regular.svg"
                },
                {
                    "name": "Aisha Johnson",
                    "description": "Certified health coach with expertise in nutrition, fitness, and mental wellbeing integration.",
                    "expertise": "Nutrition planning, Fitness routines, Mental wellbeing",
                    "is_premium": True,
                    "image_path": "img/mentors/health_wellness_coach_premium.svg"
                }
            ],
            "life_coach": [
                {
                    "name": "Jennifer Lee",
                    "description": "Life coach helping clients discover their purpose and create meaningful life changes.",
                    "expertise": "Purpose discovery, Goal setting, Personal transformation",
                    "is_premium": False,
                    "image_path": "img/mentors/life_coach_regular.svg"
                },
                {
                    "name": "Marcus Brown",
                    "description": "Transformational coach specializing in overcoming limiting beliefs and achieving breakthrough results.",
                    "expertise": "Mindset transformation, Personal growth, Overcoming obstacles",
                    "is_premium": True,
                    "image_path": "img/mentors/life_coach_premium.svg"
                }
            ],
            "astrology_expert": [
                {
                    "name": "Ravi Shastri",
                    "description": "Astrology expert with over 10 years of experience interpreting natal charts and planetary transits.",
                    "expertise": "Birth chart analysis, Compatibility readings, Transit forecasts",
                    "is_premium": False,
                    "image_path": "img/mentors/astrology_expert_regular.svg"
                },
                {
                    "name": "Riya Pandit",
                    "description": "Advanced astrological counselor specializing in career and relationship guidance through cosmic patterns.",
                    "expertise": "Career astrology, Relationship compatibility, Life path guidance",
                    "is_premium": True,
                    "image_path": "img/mentors/astrology_expert_premium.svg"
                }
            ],
            "creative_thinking_coach": [
                {
                    "name": "Zoe Richards",
                    "description": "Creative thinking coach who helps professionals break through creative blocks and develop innovative solutions.",
                    "expertise": "Creative problem solving, Innovation techniques, Design thinking",
                    "is_premium": False,
                    "image_path": "img/mentors/creative_thinking_coach_regular.svg"
                },
                {
                    "name": "Raj Patel",
                    "description": "Innovation specialist with background in product design and creative leadership.",
                    "expertise": "Creative leadership, Innovation frameworks, Ideation techniques",
                    "is_premium": True,
                    "image_path": "img/mentors/creative_thinking_coach_premium.svg"
                }
            ]
        }

        # Ensure directory exists for mentor images
        target_dir = os.path.join(settings.STATICFILES_DIRS[0], "img/mentor_images")
        os.makedirs(target_dir, exist_ok=True)

        for mentor_type, mentors in mentors_data.items():
            for mentor_info in mentors:
                mentor, created = Mentor.objects.update_or_create(
                    name=mentor_info['name'],
                    type=mentor_type,
                    defaults={
                        'description': mentor_info['description'],
                        'expertise': mentor_info['expertise'],
                        'is_premium': mentor_info['is_premium']
                    }
                )
                
                # Add image to mentor if specified
                if 'image_path' in mentor_info:
                    source_path = os.path.join(settings.STATICFILES_DIRS[0], mentor_info['image_path'])
                    if os.path.exists(source_path):
                        # Get the file name from the path
                        file_name = os.path.basename(source_path)
                        
                        # Generate target path in the mentor_images directory
                        target_path = os.path.join(target_dir, file_name)
                        
                        # Copy the file to the mentor_images directory
                        shutil.copyfile(source_path, target_path)
                        
                        # Set the image field to the filename
                        mentor.image = file_name
                        mentor.save()
                        
                        self.stdout.write(self.style.SUCCESS(f'Added image to mentor: {mentor.name} -> {file_name}'))
                    else:
                        self.stdout.write(self.style.WARNING(f'Image not found for mentor {mentor.name}: {source_path}'))
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created mentor: {mentor.name}'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'Updated mentor: {mentor.name}'))

        self.stdout.write(self.style.SUCCESS('Successfully added mentors')) 