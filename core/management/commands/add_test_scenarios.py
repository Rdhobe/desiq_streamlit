from django.core.management.base import BaseCommand
from core.models import Scenario, ScenarioOption
import random
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Add test scenarios to the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=30,
            help='Number of scenarios to create'
        )

    def handle(self, *args, **options):
        count = options['count']
        
        # Check existing scenarios
        existing_count = Scenario.objects.count()
        self.stdout.write(f"Current scenario count: {existing_count}")
        
        if existing_count >= count:
            self.stdout.write(self.style.WARNING(f"Already have {existing_count} scenarios. Skipping creation."))
            return
        
        scenarios_to_create = count - existing_count
        self.stdout.write(f"Creating {scenarios_to_create} test scenarios...")
        
        # Define categories
        categories = ['career', 'finance', 'relationships', 'time_management', 
                     'education', 'health', 'ethics', 'other']
        
        # Define difficulties
        difficulties = ['easy', 'medium', 'hard']
        
        # Create scenarios
        created_count = 0
        
        for i in range(scenarios_to_create):
            try:
                # Generate scenario data
                category = random.choice(categories)
                difficulty = random.choice(difficulties)
                level_requirement = random.randint(1, 10)
                
                # Create scenario title and description
                title = f"Test Scenario {existing_count + i + 1}: {category.capitalize()} Decision"
                description = f"This is a test scenario for the {category} category with {difficulty} difficulty."
                
                # Create the scenario
                scenario = Scenario.objects.create(
                    title=title,
                    description=description,
                    category=category,
                    difficulty=difficulty,
                    xp_reward=random.randint(10, 50),
                    unlocked_at_level=level_requirement
                )
                
                # Create 3-4 options for this scenario
                num_options = random.randint(3, 4)
                
                for j in range(num_options):
                    option_text = f"Option {j+1} for scenario {scenario.id}"
                    
                    # Generate random scores for this option
                    ScenarioOption.objects.create(
                        scenario=scenario,
                        text=option_text,
                        rationality_points=random.randint(1, 10),
                        decisiveness_points=random.randint(1, 10),
                        empathy_points=random.randint(1, 10),
                        clarity_points=random.randint(1, 10)
                    )
                
                created_count += 1
                
                # Progress indicator
                if created_count % 10 == 0 or created_count == scenarios_to_create:
                    self.stdout.write(f"Created {created_count}/{scenarios_to_create} scenarios...")
                
            except Exception as e:
                logger.error(f"Error creating test scenario: {str(e)}")
                self.stdout.write(self.style.ERROR(f"Error creating scenario {i+1}: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS(f"Successfully created {created_count} test scenarios")) 