from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Profile, UserScenarioProgress, UserTestResult, PersonalityTest, PersonalityTestResult
from django.utils import timezone
import random
import json
from datetime import timedelta
from faker import Faker
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Add fake users with complete profiles to the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=2000,
            help='Number of fake users to create'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if user count is already above the target'
        )

    def handle(self, *args, **options):
        target_count = options['count']
        force = options['force']
        
        # Check current user count
        current_count = User.objects.count()
        self.stdout.write(f"Current user count: {current_count}")
        
        if current_count >= target_count and not force:
            self.stdout.write(self.style.WARNING(f"User count already at or above target ({current_count} >= {target_count}). Use --force to override."))
            return
        
        # Calculate how many users to create
        users_to_create = target_count - current_count
        if force:
            users_to_create = target_count
            
        self.stdout.write(f"Creating {users_to_create} fake users...")
        
        # Initialize Faker with Indian locale
        fake = Faker('en_IN')
        
        # Common Indian first names
        indian_first_names = [
            'Aarav', 'Vivaan', 'Aditya', 'Vihaan', 'Arjun', 'Reyansh', 'Ayaan', 'Atharva', 'Krishna', 'Ishaan',
            'Shaurya', 'Advik', 'Rudra', 'Pranav', 'Advaith', 'Aryan', 'Dhruv', 'Kabir', 'Ritvik', 'Aarush',
            'Kian', 'Darsh', 'Veer', 'Samarth', 'Aadya', 'Diya', 'Ananya', 'Saanvi', 'Aadhya', 'Aaradhya',
            'Anvi', 'Aanya', 'Pari', 'Myra', 'Sara', 'Siya', 'Divya', 'Kavya', 'Khushi', 'Meera',
            'Prisha', 'Zara', 'Riya', 'Ira', 'Ahana', 'Isha', 'Aisha', 'Kiara', 'Maryam', 'Sanjana',
            'Alisha', 'Anaya', 'Trisha', 'Amaira', 'Anushka', 'Neha', 'Pooja', 'Shreya', 'Tanvi', 'Rhea'
        ]
        
        # Common Indian last names
        indian_last_names = [
            'Sharma', 'Verma', 'Patel', 'Gupta', 'Singh', 'Kumar', 'Shah', 'Joshi', 'Rao', 'Reddy',
            'Nair', 'Menon', 'Pillai', 'Iyer', 'Iyengar', 'Agarwal', 'Banerjee', 'Chatterjee', 'Mukherjee', 'Sengupta',
            'Dasgupta', 'Das', 'Bose', 'Dutta', 'Dey', 'Choudhury', 'Desai', 'Mehta', 'Jain', 'Malhotra',
            'Kapoor', 'Khanna', 'Chopra', 'Bedi', 'Sethi', 'Anand', 'Gill', 'Bajwa', 'Grewal', 'Sidhu',
            'Chawla', 'Mehra', 'Arora', 'Sood', 'Ahuja', 'Bhalla', 'Kaur', 'Kohli', 'Wadhwa', 'Suri'
        ]
        
        # Get available personality tests
        tests = list(PersonalityTest.objects.all())
        if not tests:
            self.stdout.write(self.style.WARNING("No personality tests found. Run add_personality_tests first."))
        
        # Create users with profiles
        created_count = 0
        premium_count = 0
        
        for i in range(users_to_create):
            try:
                # Progress indicator
                if (i + 1) % 100 == 0 or i + 1 == users_to_create:
                    self.stdout.write(f"Created {i + 1}/{users_to_create} users...")
                
                # Generate Indian user data
                first_name = random.choice(indian_first_names)
                last_name = random.choice(indian_last_names)
                username = f"{first_name.lower()}{last_name.lower()}{random.randint(1, 9999)}"
                email = f"{username}@{fake.domain_name()}"
                
                # Create user
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password='password123',
                    first_name=first_name,
                    last_name=last_name
                )
                
                # Decide if premium (20% chance)
                is_premium = random.random() < 0.2
                if is_premium:
                    premium_count += 1
                
                # Calculate profile stats based on user ID for variety
                user_seed = user.id * 13  # Use ID as seed for deterministic but varied values
                random.seed(user_seed)
                
                level = random.randint(1, 20)
                xp_points = level * 100 + random.randint(0, 99)
                daily_streak = random.randint(0, 30)
                
                # Create profile with randomized data
                profile = Profile.objects.get(user=user)
                profile.level = level
                profile.xp_points = xp_points
                profile.daily_streak = daily_streak
                profile.rationality_score = random.randint(10, 100)
                profile.decisiveness_score = random.randint(10, 100)
                profile.empathy_score = random.randint(10, 100)
                profile.clarity_score = random.randint(10, 100)
                profile.total_scenarios_completed = random.randint(5, 50)
                profile.is_premium = is_premium
                
                # Set premium expiration date for premium users
                if is_premium:
                    profile.premium_expires = timezone.now() + timedelta(days=random.randint(1, 365))
                    profile.payment_method_id = f"pm_{fake.uuid4()}"
                
                # Set MBTI type
                mbti_types = ['INTJ', 'INTP', 'ENTJ', 'ENTP', 'INFJ', 'INFP', 'ENFJ', 'ENFP', 
                             'ISTJ', 'ISFJ', 'ESTJ', 'ESFJ', 'ISTP', 'ISFP', 'ESTP', 'ESFP']
                profile.mbti_type = random.choice(mbti_types)
                
                # Set decision style
                decision_styles = ['Analytical', 'Intuitive', 'Directive', 'Conceptual', 'Behavioral']
                profile.decision_style = random.choice(decision_styles)
                
                # Set primary bias
                biases = ['Confirmation Bias', 'Anchoring Bias', 'Availability Heuristic', 
                         'Dunning-Kruger Effect', 'Optimism Bias', 'Loss Aversion',
                         'Bandwagon Effect', 'Status Quo Bias', 'Hindsight Bias']
                profile.primary_bias = random.choice(biases)
                
                # Set activity timestamp
                profile.last_activity = timezone.now() - timedelta(days=random.randint(0, 30))
                
                # Save profile
                profile.save()
                
                # Add personality test results if tests exist
                if tests:
                    # Take 1-3 tests
                    num_tests = random.randint(1, min(3, len(tests)))
                    random_tests = random.sample(tests, num_tests)
                    
                    for test in random_tests:
                        # Create or get a result for this test
                        result_title = f"{test.title} Result for {user.first_name}"
                        
                        # Create fake result data
                        result_data = {
                            "title": result_title,
                            "description": f"Personalized analysis for {user.first_name}",
                            "traits": {
                                "openness": random.randint(30, 95),
                                "conscientiousness": random.randint(30, 95),
                                "extraversion": random.randint(30, 95),
                                "agreeableness": random.randint(30, 95),
                                "neuroticism": random.randint(30, 95)
                            },
                            "strengths": [
                                fake.sentence(nb_words=3),
                                fake.sentence(nb_words=3),
                                fake.sentence(nb_words=3),
                                fake.sentence(nb_words=3)
                            ],
                            "weaknesses": [
                                fake.sentence(nb_words=3),
                                fake.sentence(nb_words=3),
                                fake.sentence(nb_words=3),
                                fake.sentence(nb_words=3)
                            ],
                            "recommendations": [
                                {"title": fake.sentence(nb_words=2), "description": fake.sentence()},
                                {"title": fake.sentence(nb_words=2), "description": fake.sentence()},
                                {"title": fake.sentence(nb_words=2), "description": fake.sentence()}
                            ],
                            "compatibility": random.randint(50, 95),
                            "accuracy": random.choice(["Low", "Medium", "High"])
                        }
                        
                        # Create test result
                        result, _ = PersonalityTestResult.objects.get_or_create(
                            test=test,
                            title=result_title,
                            defaults={'description': json.dumps(result_data)}
                        )
                        
                        # Create user test result
                        test_date = timezone.now() - timedelta(days=random.randint(1, 60))
                        UserTestResult.objects.create(
                            user=user,
                            test=test,
                            result=result,
                            timestamp=test_date,
                            answers={}  # Empty answers dict as we're creating fake results
                        )
                
                created_count += 1
                
            except Exception as e:
                logger.error(f"Error creating fake user: {str(e)}")
                self.stdout.write(self.style.ERROR(f"Error creating user {i+1}: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS(f"Successfully created {created_count} fake users ({premium_count} premium)")) 