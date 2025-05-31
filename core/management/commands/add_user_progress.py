from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Profile, Scenario, ScenarioOption, UserScenarioProgress
from django.utils import timezone
import random
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Add scenario progress for existing users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--min-scenarios',
            type=int,
            default=5,
            help='Minimum number of scenarios per user'
        )
        parser.add_argument(
            '--max-scenarios',
            type=int,
            default=20,
            help='Maximum number of scenarios per user'
        )

    def handle(self, *args, **options):
        min_scenarios = options['min_scenarios']
        max_scenarios = options['max_scenarios']
        
        # Get all users and scenarios
        users = User.objects.all()
        scenarios = list(Scenario.objects.all())
        
        if not scenarios:
            self.stdout.write(self.style.ERROR("No scenarios found in the database. Cannot add progress."))
            return
        
        self.stdout.write(f"Adding scenario progress for {users.count()} users...")
        
        # Track progress
        users_updated = 0
        total_progress_added = 0
        
        for user in users:
            try:
                # Get user profile
                profile = Profile.objects.get(user=user)
                
                # Check existing progress
                existing_progress = UserScenarioProgress.objects.filter(user=user).count()
                
                # Determine how many scenarios to add
                target_scenarios = random.randint(min_scenarios, max_scenarios)
                scenarios_to_add = max(0, target_scenarios - existing_progress)
                
                if scenarios_to_add <= 0:
                    continue
                
                # Get available scenarios (those without progress)
                completed_scenario_ids = UserScenarioProgress.objects.filter(
                    user=user
                ).values_list('scenario_id', flat=True)
                
                available_scenarios = [s for s in scenarios if s.id not in completed_scenario_ids]
                
                # If we don't have enough available scenarios, use what we have
                scenarios_to_add = min(scenarios_to_add, len(available_scenarios))
                
                if scenarios_to_add <= 0:
                    continue
                
                # Select random scenarios
                selected_scenarios = random.sample(available_scenarios, scenarios_to_add)
                
                # Add progress for each scenario
                for scenario in selected_scenarios:
                    # Get options for this scenario
                    options = list(ScenarioOption.objects.filter(scenario=scenario))
                    
                    if not options:
                        continue
                    
                    # Select a random option
                    selected_option = random.choice(options)
                    
                    # Create progress record
                    completion_date = timezone.now() - timedelta(days=random.randint(1, 60))
                    progress = UserScenarioProgress.objects.create(
                        user=user,
                        scenario=scenario,
                        completed=True,
                        selected_option=selected_option,
                        completed_at=completion_date,
                        attempts=random.randint(1, 3),
                        last_attempt_date=completion_date.date()
                    )
                    
                    # Update profile stats
                    profile.rationality_score += selected_option.rationality_points
                    profile.decisiveness_score += selected_option.decisiveness_points
                    profile.empathy_score += selected_option.empathy_points
                    profile.clarity_score += selected_option.clarity_points
                    profile.total_scenarios_completed += 1
                    
                    # Add XP
                    profile.xp_points += scenario.xp_reward
                    
                    total_progress_added += 1
                
                # Update level based on XP
                profile.level = (profile.xp_points // 100) + 1
                
                # Normalize scores to be within 0-100
                profile.rationality_score = min(100, max(0, profile.rationality_score))
                profile.decisiveness_score = min(100, max(0, profile.decisiveness_score))
                profile.empathy_score = min(100, max(0, profile.empathy_score))
                profile.clarity_score = min(100, max(0, profile.clarity_score))
                
                # Save profile
                profile.save()
                
                users_updated += 1
                
                # Progress indicator
                if users_updated % 100 == 0:
                    self.stdout.write(f"Updated {users_updated} users...")
                
            except Exception as e:
                logger.error(f"Error adding progress for user {user.username}: {str(e)}")
                self.stdout.write(self.style.ERROR(f"Error for user {user.username}: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS(
            f"Successfully added {total_progress_added} scenario progress records for {users_updated} users"
        )) 