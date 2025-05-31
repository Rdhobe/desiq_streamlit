from django.core.management.base import BaseCommand
from core.models import PersonalityTest
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Add personality tests to the database'

    def handle(self, *args, **kwargs):
        tests_data = {
            "mbti": {
                "title": "Myers-Briggs Type Indicator",
                "icon": "Brain",
                "description": "The Myers-Briggs Type Indicator is a self-report questionnaire that helps identify your psychological preferences in how you perceive the world and make decisions.",
                "question_count": 16,
                "time_to_complete": "10-15 minutes",
                "unlocked_at_level": 1
            },
            "genz-vs-millennial-vs-alpha": {
                "title": "Gen Z vs Millennial vs Alpha Test",
                "icon": "Sparkles",
                "description": "This fun quiz evaluates your digital habits, cultural references, and communication style to determine if you think more like a Gen Z, Millennial, or Generation Alpha.",
                "question_count": 12,
                "time_to_complete": "5-10 minutes",
                "unlocked_at_level": 2
            },
            "decision-making": {
                "title": "Decision Making Style Assessment",
                "icon": "Workflow",
                "description": "This assessment reveals your dominant decision-making style, from analytical to intuitive, and provides insights on how to leverage your strengths.",
                "question_count": 15,
                "time_to_complete": "8-12 minutes",
                "unlocked_at_level": 3
            },
            "cognitive-bias": {
                "title": "Cognitive Bias Test",
                "icon": "Lightbulb",
                "description": "This test identifies your most prominent cognitive biases and provides personalized recommendations to improve your critical thinking.",
                "question_count": 20,
                "time_to_complete": "15-20 minutes",
                "unlocked_at_level": 4
            },
            "emotional-intelligence": {
                "title": "Emotional Intelligence Assessment",
                "icon": "Heart",
                "description": "This assessment evaluates your emotional intelligence and provides insights on how to improve your relationships, communication, and overall well-being.",
                "question_count": 18,
                "time_to_complete": "10-15 minutes",
                "unlocked_at_level": 5
            },
            "risk-tolerance": {
                "title": "Risk Tolerance Assessment",
                "icon": "TrendingUp",
                "description": "This test assesses your risk tolerance across different domains and provides personalized recommendations to help you make informed decisions.",
                "question_count": 14,
                "time_to_complete": "7-10 minutes",
                "unlocked_at_level": 6
            }
        }

        for slug, test_data in tests_data.items():
            test, created = PersonalityTest.objects.update_or_create(
                slug=slug,
                defaults={
                    'title': test_data['title'],
                    'description': test_data['description'],
                    'icon': test_data['icon'],
                    'question_count': test_data['question_count'],
                    'time_to_complete': test_data['time_to_complete']
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created test: {test.title}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Updated test: {test.title}'))

        self.stdout.write(self.style.SUCCESS('Successfully added personality tests')) 