from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth.signals import user_logged_in
import datetime
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

# Create your models here.

class PersonalityTest(models.Model):
    ICON_CHOICES = [
        ('Brain', 'Brain'),
        ('Sparkles', 'Sparkles'),
        ('Workflow', 'Workflow'),
        ('Lightbulb', 'Lightbulb'),
        ('Heart', 'Heart'),
        ('TrendingUp', 'TrendingUp'),
    ]
    
    slug = models.SlugField(unique=True, help_text="URL-friendly identifier (e.g., 'mbti', 'genz-vs-millennial')")
    title = models.CharField(max_length=100)
    description = models.TextField(help_text="Main description of the test")
    icon = models.CharField(max_length=20, choices=ICON_CHOICES, default='Brain')
    question_count = models.IntegerField(default=0, help_text="Number of questions in the test")
    time_to_complete = models.CharField(max_length=50, blank=True, help_text="Estimated time to complete (e.g., '5 minutes')")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='personality_test_images/', null=True, blank=True)
    unlocked_at_level = models.IntegerField(default=1, help_text="Minimum level required to unlock this test")

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title
    
class PersonalityTestQuestion(models.Model):
    test = models.ForeignKey(PersonalityTest, on_delete=models.CASCADE, related_name='questions')
    question = models.TextField()
    options = models.JSONField()
    order = models.IntegerField(default=0, help_text="Order in which questions appear")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.question
    
class PersonalityTestAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_answers')
    question = models.ForeignKey(PersonalityTestQuestion, on_delete=models.CASCADE)
    answer = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s answer to {self.question}"

class PersonalityTestResult(models.Model):
    test = models.ForeignKey(PersonalityTest, on_delete=models.CASCADE, related_name='results')
    title = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='test_result_images/', null=True, blank=True)

    def __str__(self):
        return f"{self.test.title} - {self.title}"
    
class UserTestResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_results')
    test = models.ForeignKey(PersonalityTest, on_delete=models.CASCADE)
    result = models.ForeignKey(PersonalityTestResult, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    answers = models.JSONField(null=True, blank=True, help_text="JSON containing answers and scores")
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user.username}'s result for {self.test.title}"

class Tag(models.Model):
    name = models.CharField(max_length=50)
    def __str__(self):
        return self.name

class Mentor(models.Model):
    """Model for mentors that users can chat with"""
    MENTOR_TYPES = [
        ('career_coach', 'Career Coach'),
        ('financial_advisor', 'Financial Advisor'),
        ('relationship_counselor', 'Relationship Counselor'),
        ('time_management_expert', 'Time Management Expert'),
        ('educational_consultant', 'Educational Consultant'),
        ('health_wellness_coach', 'Health & Wellness Coach'),
        ('life_coach', 'Life Coach'),
        ('astrology_expert', 'Astrology Expert'),
        ('creative_thinking_coach', 'Creative Thinking Coach'),
    ]
    
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=50, choices=MENTOR_TYPES)
    description = models.TextField()
    expertise = models.CharField(max_length=200)
    image = models.CharField(max_length=255, blank=True, null=True, 
                            help_text="Path to image file in static/img/mentor_images/ directory")
    is_premium = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"
    
    def get_image_url(self):
        """Return the static URL for the mentor image"""
        if not self.image:
            # Return default image based on mentor type and premium status
            premium_suffix = "premium" if self.is_premium else "regular"
            return f"/static/img/mentor_images/{self.type}_{premium_suffix}.svg"
        return f"/static/img/mentor_images/{self.image}"

class Item(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    xp_points = models.IntegerField(default=0)
    rationality_score = models.IntegerField(default=0)
    decisiveness_score = models.IntegerField(default=0)
    empathy_score = models.IntegerField(default=0)
    clarity_score = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    daily_streak = models.IntegerField(default=0)
    last_login_date = models.DateField(auto_now_add=True)
    last_activity = models.DateTimeField(default=timezone.now, help_text="Last time the user was active on the site")
    is_premium = models.BooleanField(default=False, db_index=True)
    
    # User preferences
    mbti_type = models.CharField(max_length=10, blank=True, null=True)
    decision_style = models.CharField(max_length=20, blank=True, null=True)
    primary_bias = models.CharField(max_length=20, blank=True, null=True)
    
    # Subscription fields
    premium_plan = models.CharField(max_length=20, choices=[('monthly', 'Monthly'), ('annual', 'Annual')], blank=True, null=True)
    premium_expires = models.DateTimeField(null=True, blank=True, db_index=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    payment_method_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Add these fields at the appropriate place in the existing Profile model
    rank = models.PositiveIntegerField(default=0)
    total_scenarios_completed = models.PositiveIntegerField(default=0)
    total_comments = models.PositiveIntegerField(default=0)
    total_likes_received = models.PositiveIntegerField(default=0)
    total_posts = models.PositiveIntegerField(default=0)
    
    class Meta:
        indexes = [
            models.Index(fields=['level']),
            models.Index(fields=['xp_points']),
            models.Index(fields=['last_activity']),
        ]
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

    def has_active_subscription(self):
        if self.is_premium and self.premium_expires:
            return self.premium_expires > timezone.now()
        return False
        
    def cancel_subscription(self):
        self.is_premium = False
        self.premium_expires = None
        self.stripe_subscription_id = None
        self.save()
        
    def activate_subscription(self, plan_type, duration_days=30):
        self.is_premium = True
        self.premium_plan = plan_type
        
        # Set expiration date
        if self.premium_expires and self.premium_expires > timezone.now():
            # Extend existing subscription
            self.premium_expires = self.premium_expires + datetime.timedelta(days=duration_days)
        else:
            # New subscription
            self.premium_expires = timezone.now() + datetime.timedelta(days=duration_days)
            
        self.save()

    @property
    def activity_score(self):
        """Calculate activity score based on various metrics"""
        score = (
            self.xp_points * 1 +
            self.daily_streak * 10 +
            self.total_scenarios_completed * 5 +
            self.total_comments * 2 +
            self.total_likes_received * 1 +
            self.total_posts * 3
        )
        return score

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

@receiver(user_logged_in)
def user_logged_in_handler(sender, request, user, **kwargs):
    """Generate daily challenges when a user logs in if they don't have any for today"""
    # Skip this process for admin/staff users
    if user.is_staff:
        return
        
    # Update last login date and check streak
    profile = user.profile
    today = timezone.now().date()
    yesterday = today - timezone.timedelta(days=1)
    
    # Update streak if user logged in yesterday or today is their first login
    if profile.last_login_date == yesterday:
        profile.daily_streak += 1
    elif profile.last_login_date < yesterday:
        # Reset streak if user missed a day
        profile.daily_streak = 1
    
    # Update last login date
    profile.last_login_date = today
    profile.save()
    
    # Check if user has daily challenges for today
    from core.models import DailyChallenge
    daily_challenges = DailyChallenge.objects.filter(
        user=user,
        date_created=today
    )
    
    # If no challenges exist for today, generate them
    if not daily_challenges.exists():
        try:
            from core.utils import generate_daily_challenges_for_user
            # Determine number of challenges based on premium status
            num_challenges = 3 if profile.is_premium else 1
            generate_daily_challenges_for_user(user, num_challenges)
        except Exception as e:
            # Log the error but don't prevent login
            print(f"Error generating daily challenges for {user.username}: {str(e)}")

class Scenario(models.Model):
    CATEGORY_CHOICES = [
        ('career', 'Career Decisions'),
        ('finance', 'Financial Decisions'),
        ('relationships', 'Relationship Decisions'),
        ('time_management', 'Time Management'),
        ('education', 'Educational Decisions'),
        ('health', 'Health & Wellness'),
        ('ethics', 'Ethics'),
        ('other', 'Other'),
    ]
    
    DIFFICULTY_CHOICES = [
        (1, 'Easy'),
        (2, 'Medium'),
        (3, 'Hard'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    difficulty = models.IntegerField(choices=DIFFICULTY_CHOICES, default=1)
    xp_reward = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    unlocked_at_level = models.IntegerField(default=1, help_text="Minimum level required to unlock this scenario")
    
    def __str__(self):
        return self.title

class ScenarioOption(models.Model):
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name='options')
    text = models.TextField()
    rationality_points = models.IntegerField(default=0)
    decisiveness_points = models.IntegerField(default=0)
    empathy_points = models.IntegerField(default=0)
    clarity_points = models.IntegerField(default=0)
    feedback = models.TextField()
    next_scenario = models.ForeignKey(Scenario, on_delete=models.SET_NULL, null=True, blank=True, 
                                     related_name='previous_options', 
                                     help_text="Next scenario to show based on this option")
    
    def __str__(self):
        return f"Option for {self.scenario.title}"

class UserScenarioProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scenario_progress')
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False, db_index=True)
    selected_option = models.ForeignKey(ScenarioOption, on_delete=models.SET_NULL, null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    attempts = models.IntegerField(default=0, help_text="Number of times the user has attempted this scenario")
    last_attempt_date = models.DateField(null=True, blank=True, help_text="Date of the last attempt", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'scenario')
        indexes = [
            models.Index(fields=['user', 'completed']),
            models.Index(fields=['completed_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username}'s progress on {self.scenario.title}"

class DailyChallenge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_challenges')
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE)
    date_created = models.DateField(default=timezone.now, db_index=True)
    completed = models.BooleanField(default=False, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('user', 'scenario', 'date_created')
        indexes = [
            models.Index(fields=['user', 'date_created']),
            models.Index(fields=['user', 'completed']),
        ]
    
    def __str__(self):
        return f"{self.user.username}'s challenge on {self.date_created}: {self.scenario.title}"
    
    @property
    def is_locked(self):
        """Check if the challenge is locked (attempted but not completed or already completed)"""
        if self.completed:
            return True
        
        # Check if there's a progress record for this scenario
        progress = UserScenarioProgress.objects.filter(user=self.user, scenario=self.scenario).first()
        return progress is not None

class DailyUsageTracker(models.Model):
    """Track daily usage limits for scenarios"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='usage_trackers')
    date = models.DateField(default=timezone.now)
    scenarios_generated = models.IntegerField(default=0, help_text="Number of scenarios generated today")
    scenarios_attempted = models.IntegerField(default=0, help_text="Number of scenarios attempted today")
    
    class Meta:
        unique_together = ('user', 'date')
        
    def __str__(self):
        return f"{self.user.username}'s usage on {self.date}"
    
    @classmethod
    def get_for_user(cls, user, date=None):
        """Get or create a usage tracker for the user on the specified date"""
        if date is None:
            date = timezone.now().date()
        
        tracker, created = cls.objects.get_or_create(
            user=user,
            date=date
        )
        return tracker
    
    def can_generate_scenario(self):
        """Check if the user can generate a new scenario today"""
        limit = 5 if self.user.profile.is_premium else 2
        return self.scenarios_generated < limit
    
    def can_attempt_scenario(self):
        """Check if the user can attempt a scenario today"""
        limit = 5 if self.user.profile.is_premium else 2
        return self.scenarios_attempted < limit

class MentorChatUsage(models.Model):
    """Track daily mentor chat usage"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mentor_chat_usage')
    mentor = models.ForeignKey(Mentor, on_delete=models.CASCADE, related_name='chat_usage')
    date = models.DateField(default=timezone.now)
    messages_sent = models.IntegerField(default=0, help_text="Number of messages sent to this mentor today")
    
    class Meta:
        unique_together = ('user', 'mentor', 'date')
        
    def __str__(self):
        return f"{self.user.username}'s chat with {self.mentor.name} on {self.date}"
    
    @classmethod
    def get_for_user_mentor(cls, user, mentor, date=None):
        """Get or create a chat usage tracker for the user and mentor on the specified date"""
        if date is None:
            date = timezone.now().date()
        
        tracker, created = cls.objects.get_or_create(
            user=user,
            mentor=mentor,
            date=date
        )
        return tracker
    
    def can_send_message(self):
        """Check if the user can send more messages to this mentor today"""
        if self.mentor.is_premium and not self.user.profile.is_premium:
            return False  # Free users can't chat with premium mentors
        
        # Daily message limits
        limit = 20 if self.user.profile.is_premium else 5
        return self.messages_sent < limit
        
    def remaining_messages(self):
        """Get the number of remaining messages the user can send to this mentor today"""
        limit = 20 if self.user.profile.is_premium else 5
        return max(0, limit - self.messages_sent)

class MentorChat(models.Model):
    """Model to store chat history between users and mentors"""
    MESSAGE_TYPES = [
        ('user', 'User'),
        ('mentor', 'Mentor'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mentor_chats')
    mentor = models.ForeignKey(Mentor, on_delete=models.CASCADE, related_name='chats')
    message = models.TextField()
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.get_message_type_display()} message in chat between {self.user.username} and {self.mentor.name}"

class DirectMessage(models.Model):
    """Model for direct messages between users"""
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_direct_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_direct_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    # For sharing scenarios/reports
    shared_scenario = models.ForeignKey(Scenario, on_delete=models.SET_NULL, null=True, blank=True, related_name='shared_in_direct_messages')
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"Message from {self.sender.username} to {self.recipient.username}"
    
    @staticmethod
    def get_conversation(user1, user2):
        """Get all messages between two users"""
        return DirectMessage.objects.filter(
            (models.Q(sender=user1) & models.Q(recipient=user2)) | 
            (models.Q(sender=user2) & models.Q(recipient=user1))
        ).order_by('timestamp')

class SupportIssue(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    ISSUE_TYPE_CHOICES = [
        ('bug', 'Bug Report'),
        ('feature', 'Feature Request'),
        ('question', 'Question'),
        ('feedback', 'Feedback'),
        ('contact', 'Contact Form'),
        ('other', 'Other'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_issues')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    issue_type = models.CharField(max_length=20, choices=ISSUE_TYPE_CHOICES, default='other')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.title} - {self.user.username} ({self.get_status_display()})"
    
class IssueComment(models.Model):
    issue = models.ForeignKey(SupportIssue, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='issue_comments')
    comment = models.TextField()
    is_staff_comment = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        
    def __str__(self):
        return f"Comment by {self.user.username} on {self.issue.title}"

class ChatRoom(models.Model):
    ROOM_TYPES = [
        ('personal', 'Personal Chat'),
        ('group', 'Group Chat'),
        ('public', 'Public Room'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_rooms')
    participants = models.ManyToManyField(User, related_name='chat_rooms')
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default='group')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_room_type_display()})"

class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"Message from {self.sender.username} in {self.room.name}"

class UserActivity(models.Model):
    ACTIVITY_TYPES = [
        ('login', 'Login'),
        ('post', 'Post'),
        ('comment', 'Comment'),
        ('join_group', 'Join Group'),
        ('like', 'Like'),
        ('message', 'Message'),
        ('chat', 'Chat'),
        ('scenario', 'Scenario'),
        ('assessment', 'Assessment'),
        ('level_up', 'Level Up'),
        ('support_issue', 'Support Issue'),
        ('issue_comment', 'Issue Comment'),
        # Admin action types
        ('ran_add_fake_users', 'Generated Fake Users'),
        ('ran_add_mentors', 'Added Default Mentors'),
        ('ran_add_test_scenarios', 'Generated Test Scenarios'),
        ('ran_add_personality_tests', 'Added Default Personality Tests'),
        ('ran_add_user_progress', 'Added User Progress'),
        ('ran_setup_demo_data', 'Setup All Demo Data'),
        ('database_backup', 'Database Backup'),
        ('clear_cache', 'Cleared Cache'),
        ('set_user_premium', 'Set User Premium'),
        ('set_user_free', 'Set User Free'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'User activities'
    
    def __str__(self):
        return f"{self.user.username} - {self.get_activity_type_display()}"
    
    @classmethod
    def log_activity(cls, user, activity_type, related_object=None):
        """Helper method to log user activity"""
        activity = cls(user=user, activity_type=activity_type)
        
        if related_object:
            activity.content_object = related_object
            
        activity.save()
        return activity

class DynamicScenario(models.Model):
    """Model for storing dynamic scenarios with multiple questions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dynamic_scenarios')
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=Scenario.CATEGORY_CHOICES)
    difficulty = models.IntegerField(choices=Scenario.DIFFICULTY_CHOICES, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    current_question = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=0)
    
    # Final report data (filled when completed)
    final_score = models.IntegerField(null=True, blank=True)
    rationality_score = models.IntegerField(null=True, blank=True)
    decisiveness_score = models.IntegerField(null=True, blank=True)
    empathy_score = models.IntegerField(null=True, blank=True)
    clarity_score = models.IntegerField(null=True, blank=True)
    strengths = models.TextField(null=True, blank=True)
    weaknesses = models.TextField(null=True, blank=True)
    improvement_plan = models.TextField(null=True, blank=True)
    resources = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    @property
    def progress_percentage(self):
        """Calculate progress percentage"""
        if self.total_questions == 0:
            return 0
        return int((self.current_question / self.total_questions) * 100)

class DynamicScenarioQuestion(models.Model):
    """Model for storing questions for dynamic scenarios"""
    scenario = models.ForeignKey(DynamicScenario, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"Question {self.order} for {self.scenario.title}"

class DynamicScenarioAnswer(models.Model):
    """Model for storing user answers to dynamic scenario questions"""
    question = models.ForeignKey(DynamicScenarioQuestion, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    # AI evaluation of the answer (optional)
    rationality_score = models.IntegerField(null=True, blank=True)
    decisiveness_score = models.IntegerField(null=True, blank=True)
    empathy_score = models.IntegerField(null=True, blank=True)
    clarity_score = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"Answer to question {self.question.order} for {self.question.scenario.title}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=[
        ('welcome', 'Welcome'),
        ('profile', 'Profile Update'),
        ('scenario', 'Scenario Complete'),
        ('level_up', 'Level Up'),
        ('daily_challenge', 'Daily Challenge'),
        ('system', 'System Notification')
    ])
    is_read = models.BooleanField(default=False, db_index=True)
    is_email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['notification_type']),
        ]
    
    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"
    
    def mark_as_read(self):
        self.is_read = True
        self.save()
        
    @classmethod
    def create_notification(cls, user, title, message, notification_type, send_email=True):
        """Create a notification and optionally send an email"""
        notification = cls.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type
        )
        
        if send_email:
            from .utils import send_notification_email
            send_notification_email(notification)
            notification.is_email_sent = True
            notification.save()
            
        return notification

class Conversation(models.Model):
    """Model for tracking conversations between users"""
    initiator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='initiated_conversations')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_conversations')
    last_message = models.TextField(blank=True, null=True)
    last_message_time = models.DateTimeField(auto_now=True)
    unread_count = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('initiator', 'receiver')
        ordering = ['-last_message_time']
    
    def __str__(self):
        return f"Conversation between {self.initiator.username} and {self.receiver.username}"
    
    @classmethod
    def get_conversation(cls, user1, user2):
        """Get or create conversations between two users"""
        # Check both directions (user1 to user2 and user2 to user1)
        try:
            return cls.objects.get(initiator=user1, receiver=user2)
        except cls.DoesNotExist:
            try:
                return cls.objects.get(initiator=user2, receiver=user1)
            except cls.DoesNotExist:
                # Create both directions to make lookups easier
                conv1 = cls.objects.create(initiator=user1, receiver=user2)
                cls.objects.create(initiator=user2, receiver=user1)
                return conv1

class CommunityMessage(models.Model):
    """Model for storing community chat messages"""
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Community message from {self.sender.username} at {self.timestamp}"
