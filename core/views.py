from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required 
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache, cache_page
from django.contrib import messages
from django.utils import timezone
from .models import Item, Profile, Scenario, ScenarioOption, UserScenarioProgress, DailyChallenge, DailyUsageTracker, Mentor, MentorChatUsage, MentorChat, DirectMessage, SupportIssue, IssueComment, ChatRoom, ChatMessage, UserActivity, Conversation
from .forms import CustomUserCreationForm, IssueForm, IssueCommentForm
from .models import Mentor
from .models import PersonalityTest, PersonalityTestQuestion, PersonalityTestAnswer, PersonalityTestResult, UserTestResult
import razorpay
from django.conf import settings
from datetime import timedelta, datetime
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.models import User
from django.db.models import Q, Count, Max, F, OuterRef, Subquery
from django.core.exceptions import MultipleObjectsReturned
import json
import time
import os
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import DynamicScenario, DynamicScenarioQuestion, DynamicScenarioAnswer
from .utils import generate_dynamic_scenario, generate_next_question, evaluate_answer, generate_final_report, log_request_performance
from django.db import connection, transaction
import logging
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site
from social_core.exceptions import AuthException
from .models import Notification, DirectMessage, ChatMessage
from .models import CommunityMessage
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.cache import cache
import hashlib
from django.db import models

# Razorpay setup
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# Global dictionary to store message queues for each conversation
message_queues = {}

logger = logging.getLogger(__name__)

@login_required
@cache_page(60 * 5)  # Cache this view for 5 minutes
@log_request_performance
def scenarios_view(request):
    # Get user profile
    profile = request.user.profile
    user_level = profile.level
    is_premium = profile.is_premium
    
    # Check if we have cached user progress data for performance
    progress_cache_key = f"user_{request.user.id}_scenario_progress"
    completed_scenarios = cache.get(progress_cache_key)
    
    if completed_scenarios is None:
        # Get completed scenarios for the user - cache for future use
        completed_scenarios = set(
            UserScenarioProgress.objects.filter(
                user=request.user, 
                completed=True
            ).values_list('scenario_id', flat=True)
        )
        cache.set(progress_cache_key, completed_scenarios, 300)  # Cache for 5 minutes
    
    # Get all scenarios with prefetch_related to optimize queries
    all_scenarios = Scenario.objects.prefetch_related('options')
    
    # If user is logged in, filter by level and track completed scenarios
    if request.user.is_authenticated:
        scenarios = all_scenarios.filter(unlocked_at_level__lte=user_level)
        
        # Get recent scenarios for the user - use select_related to reduce queries
        user_progress = UserScenarioProgress.objects.filter(
            user=request.user
        ).select_related('scenario').order_by('-completed_at')[:4]
        
        recent_scenarios = []
        for progress in user_progress:
            scenario = progress.scenario
            scenario.is_completed = progress.completed
            recent_scenarios.append(scenario)
        
        # If we don't have 4 scenarios yet, add some random ones
        if len(recent_scenarios) < 4:
            remaining = 4 - len(recent_scenarios)
            existing_ids = [s.id for s in recent_scenarios]
            
            # Use raw SQL for the random query to improve performance
            random_scenario_ids = list(Scenario.objects.exclude(
                id__in=existing_ids
            ).values_list('id', flat=True)[:20])
            
            # Shuffle in Python instead of using ORDER BY ? which is slow
            import random
            random.shuffle(random_scenario_ids)
            random_scenario_ids = random_scenario_ids[:remaining]
            
            random_scenarios = Scenario.objects.filter(id__in=random_scenario_ids)
            
            for scenario in random_scenarios:
                scenario.is_completed = scenario.id in completed_scenarios
                recent_scenarios.append(scenario)
    else:
        # For anonymous users, only show level 1 scenarios
        scenarios = all_scenarios.filter(unlocked_at_level=1)
        completed_scenarios = set()
        
        # Optimize random scenario selection
        level1_scenarios = list(Scenario.objects.filter(unlocked_at_level=1)[:10])
        import random
        random.shuffle(level1_scenarios)
        recent_scenarios = level1_scenarios[:4]
        
        for scenario in recent_scenarios:
            scenario.is_completed = False
    
    # Group scenarios by category - precompute in Python to avoid N+1 queries
    categories = {}
    for scenario in scenarios:
        category = scenario.get_category_display()
        if category not in categories:
            categories[category] = []
        
        # Add completion status
        scenario.is_completed = scenario.id in completed_scenarios
        categories[category].append(scenario)
    
    # Count completed scenarios
    completed_count = len(completed_scenarios)
    total_count = scenarios.count()
    
    # Calculate completion percentage
    completion_percentage = int((completed_count / total_count) * 100) if total_count > 0 else 0
    
    # Count scenarios completed today
    today = timezone.now().date()
    scenarios_completed_today = UserScenarioProgress.objects.filter(
        user=request.user,
        completed=True,
        completed_at__date=today
    ).count()
    
    # Get daily usage tracker for today
    daily_tracker = DailyUsageTracker.get_for_user(request.user, today)
    scenarios_generated_today = daily_tracker.scenarios_generated
    
    context = {
        'categories': categories,
        'recent_scenarios': recent_scenarios,
        'profile': profile,
        'user_level': user_level,
        'is_premium': is_premium,
        'completed_count': completed_count,
        'total_count': total_count,
        'completion_percentage': completion_percentage,
        'daily_scenario_limit': profile.daily_scenario_limit,
        'scenarios_completed_today': scenarios_completed_today,
        'scenarios_generated_today': scenarios_generated_today
    }
    
    return render(request, 'core/scenarios.html', context)

@login_required
def progress_view(request):
    user = request.user
    profile = user.profile
    
    # Get all user scenario progress
    user_scenarios = UserScenarioProgress.objects.filter(user=user).select_related('scenario', 'selected_option')
    completed_scenarios = user_scenarios.filter(completed=True)
    
    # Calculate skill scores over time (last 10 completed scenarios)
    recent_completed = completed_scenarios.order_by('-completed_at')[:10]
    skill_progress = []
    
    for progress in recent_completed:
        if progress.selected_option:
            skill_progress.append({
                'date': progress.completed_at,
                'rationality': progress.selected_option.rationality_points,
                'decisiveness': progress.selected_option.decisiveness_points,
                'empathy': progress.selected_option.empathy_points,
                'clarity': progress.selected_option.clarity_points,
                'scenario': progress.scenario.title
            })
    
    # Calculate XP progress percentage for current level
    current_level_xp = profile.level * 100
    next_level_xp = (profile.level + 1) * 100
    xp_for_current_level = profile.xp_points - current_level_xp
    xp_needed_for_next_level = next_level_xp - current_level_xp
    xp_progress_percentage = int((xp_for_current_level / xp_needed_for_next_level) * 100) if xp_needed_for_next_level > 0 else 0
    
    # Calculate category distribution
    category_distribution = {}
    for progress in completed_scenarios:
        category = progress.scenario.get_category_display()
        if category in category_distribution:
            category_distribution[category] += 1
        else:
            category_distribution[category] = 1
    
    # Calculate monthly goals progress
    # For this example, let's set monthly goals as completing 20 scenarios
    monthly_goal = 20
    current_month = timezone.now().month
    current_year = timezone.now().year
    monthly_completed = completed_scenarios.filter(
        completed_at__month=current_month,
        completed_at__year=current_year
    ).count()
    monthly_goal_percentage = int((monthly_completed / monthly_goal) * 100) if monthly_goal > 0 else 0
    
    # Get streak data
    streak_data = {
        'current': profile.daily_streak,
        'best': profile.daily_streak,  # Assuming we don't track best streak separately yet
    }
    
    # Get daily attempts for the last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_attempts = {}
    
    for progress in user_scenarios.filter(last_attempt_date__gte=thirty_days_ago):
        date_str = progress.last_attempt_date.strftime('%Y-%m-%d')
        if date_str in daily_attempts:
            daily_attempts[date_str] += progress.attempts
        else:
            daily_attempts[date_str] = progress.attempts
    
    # Convert to list format for chart
    daily_attempts_data = [
        {'date': date, 'attempts': attempts} 
        for date, attempts in daily_attempts.items()
    ]
    
    context = {
        'user': user,
        'profile': profile,
        'total_scenarios': user_scenarios.count(),
        'completed_scenarios': completed_scenarios.count(),
        'completed_tests': UserTestResult.objects.filter(user=user).count(),
        'skill_progress': skill_progress,
        'category_distribution': category_distribution,
        'xp': profile.xp_points,
        'level': profile.level,
        'xp_progress_percentage': xp_progress_percentage,
        'xp_for_current_level': xp_for_current_level,
        'xp_needed_for_next_level': xp_needed_for_next_level,
        'monthly_goal': monthly_goal,
        'monthly_completed': monthly_completed,
        'monthly_goal_percentage': monthly_goal_percentage,
        'streak_data': streak_data,
        'daily_attempts_data': daily_attempts_data,
        'rationality_score': profile.rationality_score,
        'decisiveness_score': profile.decisiveness_score,
        'empathy_score': profile.empathy_score,
        'clarity_score': profile.clarity_score,
    }
    
    return render(request, 'core/progress.html', context)

@login_required
def support_view(request):
    # Get all issues for the current user
    user_issues = []
    
    try:
        user_issues = SupportIssue.objects.filter(user=request.user).order_by('-created_at')
        
        # Filter by status if provided
        status = request.GET.get('status')
        if status:
            user_issues = user_issues.filter(status=status)
    except Exception as e:
        # Gracefully handle any database errors
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error loading support issues: {str(e)}")
    
    context = {
        'user_issues': user_issues
    }
    
    return render(request, 'core/support.html', context)

@login_required
def personal_chat_view(request):
    # Get all users that have conversations with the current user
    current_user = request.user
    
    # Find users with direct message conversations
    conversations = User.objects.filter(
        Q(sent_direct_messages__recipient=current_user) | 
        Q(received_direct_messages__sender=current_user)
    ).distinct()
    
    # Get the last message and unread count for each conversation
    chat_users = []
    for user in conversations:
        # Get the last message between these users
        last_message = DirectMessage.get_conversation(current_user, user).last()
        
        # Count unread messages
        unread_count = DirectMessage.objects.filter(
            sender=user,
            recipient=current_user,
            is_read=False
        ).count()
        
        chat_users.append({
            'user': user,
            'last_message': last_message,
            'unread_count': unread_count
        })
    
    # Sort by last message time (most recent first)
    chat_users.sort(key=lambda x: x['last_message'].timestamp if x['last_message'] else timezone.now(), reverse=True)
    
    # Get other users that could be messaged (exclude existing conversations)
    existing_chat_user_ids = [user.id for user in conversations]
    existing_chat_user_ids.append(current_user.id)  # Exclude self
    
    other_users = User.objects.exclude(id__in=existing_chat_user_ids)[:10]
    
    context = {
        'chat_users': chat_users,
        'other_users': other_users
    }
    
    return render(request, 'core/personal_chat.html', context)

@login_required
def direct_message_view(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    current_user = request.user
    
    # Don't allow messaging yourself
    if other_user.id == current_user.id:
        messages.warning(request, "You cannot message yourself.")
        return redirect('core:personal_chat')
    
    # Get conversation between these users
    conversation = DirectMessage.get_conversation(current_user, other_user)
    
    # Mark messages from other user as read
    DirectMessage.objects.filter(
        sender=other_user,
        recipient=current_user,
        is_read=False
    ).update(is_read=True)
    
    # Get user's scenarios to share
    user_scenarios = UserScenarioProgress.objects.filter(
        user=current_user, 
        completed=True
    ).select_related('scenario')
    
    context = {
        'other_user': other_user,
        'messages': conversation,
        'user_scenarios': user_scenarios
    }
    
    return render(request, 'core/direct_message.html', context)

@login_required
def setting_view(request):
    # Get the user profile
    user_profile = request.user.profile
    context = {
        'description': 'change your account settings',
        'status': 200,
        'user_profile': user_profile,
        'username': False,
        'password': False,

    }
    # Process account form submission
    if request.method == 'POST' and 'form_type' in request.POST:
        form_type = request.POST.get('form_type')
        
        if form_type == 'account_form':
            # Process account form
            name = request.POST.get('username', '').strip()
            # Update user info
            if name:
                request.user.username = name
                request.user.save()
                user_profile.save()
                messages.success(request, "Account information updated successfully.")
                context['username'] = True
                context['description'] = 'Your username has been updated successfully.'
                context['status'] = 200
                
                # Send profile update notification
                from .utils import send_profile_update_notification
                try:
                    send_profile_update_notification(request.user)
                    logger.info(f"Profile update notification sent to {request.user.email}")
                except Exception as e:
                    logger.error(f"Failed to send profile update notification: {str(e)}")
            
        elif form_type == 'password_form':
            # Process password form
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')
            
            # Check if current password is correct
            if not request.user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
                context['message'] = 'Current password is incorrect.'
                context['status'] = 400
                return redirect('core:setting')
            
            # Check if new passwords match
            if new_password != confirm_password:
                messages.error(request, "New passwords don't match.")
                context['message'] = "New passwords don't match."
                context['status'] = 400
                return redirect('core:setting')
            
            # Set new password
            if new_password:
                request.user.set_password(new_password)
                request.user.save()
                messages.success(request, "Password changed successfully. Please log in again.")
                context['message'] = 'Password changed successfully. Please log in again.'
                return redirect('core:login')
                
        elif form_type == 'preferences_form':
            # Process preferences form
            theme = request.POST.get('theme', 'system')
            language = request.POST.get('language', 'en')
            
            # Save preferences (would need a preferences model)
            # For now just show success message
            messages.success(request, "Preferences updated successfully.")
            return redirect('core:setting')
    
    return render(request, 'core/setting.html', context)

@login_required
def profile_view(request):
    return render(request, 'core/profile.html')

@login_required
def personality_test_view(request):
    # Get all personality tests ordered by level
    all_tests = PersonalityTest.objects.all().order_by('unlocked_at_level')
    
    # If user is logged in, mark tests as locked/unlocked based on level
    if request.user.is_authenticated:
        # Get user profile
        profile = request.user.profile
        user_level = profile.level
        is_premium = profile.is_premium
        
        logger.info(f"User level: {user_level}")
        
        # Get user's previous test results
        user_results = UserTestResult.objects.filter(user=request.user)
        completed_tests = set(user_results.values_list('test_id', flat=True))
        
        # Mark tests as completed or locked based on user level
        for test in all_tests:
            test.is_completed = test.id in completed_tests
            test.unlocked = test.unlocked_at_level <= user_level
    else:
        # For anonymous users, only show level 1 tests as unlocked
        profile = None
        is_premium = False
        user_level = 1
        for test in all_tests:
            test.is_completed = False
            test.unlocked = test.unlocked_at_level == 1
    
    # Count completed tests
    completed_count = sum(1 for test in all_tests if getattr(test, 'is_completed', False))
    total_count = len(all_tests)
    
    # Calculate completion percentage
    completion_percentage = int((completed_count / total_count) * 100) if total_count > 0 else 0
    
    context = {
        'tests': all_tests, 
        'header': 'Personality Tests',
        'user_level': user_level,
        'is_premium': is_premium,
        'completed_count': completed_count,
        'total_count': total_count,
        'completion_percentage': completion_percentage,
        'profile': profile
    }
    
    return render(request, 'core/personality_test.html', context)

@login_required
def personality_test_detail_view(request, test_slug):
    """View for a specific personality test details"""
    test = get_object_or_404(PersonalityTest, slug=test_slug)
    
    # Check if the user's level is high enough to access this test
    if request.user.profile.level < test.unlocked_at_level:
        messages.warning(request, f"This test is locked until you reach level {test.unlocked_at_level}.")
        return redirect('core:personality_test')
    
    # Check if the user has already taken this test
    previous_results = UserTestResult.objects.filter(
        user=request.user,
        test=test
    ).order_by('-timestamp').first()
    
    context = {
        'test': test,
        'previous_results': previous_results,
    }
    
    return render(request, 'core/personality_test_detail.html', context)

@login_required
def take_personality_test_view(request, test_slug):
    """View to take a personality test"""
    test = get_object_or_404(PersonalityTest, slug=test_slug)
    
    # Check if the user's level is high enough to access this test
    if request.user.profile.level < test.unlocked_at_level:
        messages.warning(request, f"This test is locked until you reach level {test.unlocked_at_level}.")
        return redirect('core:personality_test')
    
    if request.method == 'POST':
        # Process test submission
        answers = {}
        questions_data = request.session.get(f'test_{test.slug}_questions', [])
        
        if not questions_data:
            messages.error(request, "Session expired. Please start the test again.")
            return redirect('core:personality_test_detail', test_slug=test_slug)
        
        for q in questions_data:
            question_id = q['id']
            answer_key = f'question_{question_id}'
            if answer_key in request.POST:
                answer = request.POST.get(answer_key)
                answers[str(question_id)] = {
                    'question': q['question'],
                    'answer': answer,
                    'options': q['options']
                }
        
        # Generate result using GPT-4o-mini
        result_title, result_description = generate_test_result(test, answers)
        
        # Find or create a result
        result, created = PersonalityTestResult.objects.get_or_create(
            test=test,
            title=result_title,
            defaults={'description': result_description}
        )
        
        if not created and result.description != result_description:
            # Update description if it changed
            result.description = result_description
            result.save()
        
        # Save the user's test result
        user_result = UserTestResult.objects.create(
            user=request.user,
            test=test,
            result=result,
            answers=answers
        )
        
        # Award 20 XP to the user
        profile = request.user.profile
        profile.xp_points += 20
        profile.save()
        
        messages.success(request, f"Congratulations! You earned 20 XP for completing the {test.title} test.")
        
        # Clear session data
        if f'test_{test.slug}_questions' in request.session:
            del request.session[f'test_{test.slug}_questions']
            request.session.modified = True
        
        return redirect('core:personality_test_result', result_id=user_result.id)
    
    else:
        # Generate questions using GPT-4o-mini
        questions_data = generate_test_questions(test)
        
        # Store questions in session
        request.session[f'test_{test.slug}_questions'] = questions_data
        
        context = {
            'test': test,
            'questions': questions_data,
        }
        
        return render(request, 'core/take_personality_test.html', context)

@login_required
def personality_test_result_view(request, result_id):
    """View to display personality test results"""
    import json
    
    user_result = get_object_or_404(UserTestResult, id=result_id, user=request.user)
    test = user_result.test
    result = user_result.result
    
    # Parse the JSON data from the result description
    try:
        result_data = json.loads(result.description)
    except json.JSONDecodeError:
        # If not valid JSON, use the description as is
        result_data = {
            "title": result.title,
            "description": result.description,
            "traits": None,
            "strengths": None,
            "weaknesses": None,
            "recommendations": None,
            "compatibility": None,
            "accuracy": None
        }
    
    # Get other users who got the same result
    similar_users_count = UserTestResult.objects.filter(
        result=result
    ).exclude(user=request.user).values('user').distinct().count()
    
    # Get all users for sharing (excluding current user)
    users = User.objects.exclude(id=request.user.id).order_by('username')[:20]
    
    context = {
        'test': test,
        'result': result,
        'result_data': result_data,
        'user_result': user_result,
        'similar_users_count': similar_users_count,
        'date_taken': user_result.timestamp,
        'users': users,
    }
    
    return render(request, 'core/personality_test_result.html', context)

@login_required
def my_test_results_view(request):
    """View to display all test results for the current user"""
    user_results = UserTestResult.objects.filter(
        user=request.user
    ).select_related('test', 'result').order_by('-timestamp')
    
    context = {
        'user_results': user_results,
    }
    
    return render(request, 'core/my_test_results.html', context)

@login_required
def mentor_view(request):
    """Display all mentors"""
    # Get user profile and premium status
    profile = request.user.profile
    is_premium = profile.is_premium
    
    # Determine daily message quota based on premium status
    daily_limit = 20 if is_premium else 5
    
    # Get mentor types with at least one mentor
    mentor_types = Mentor.objects.values_list('type', flat=True).distinct()
    
    # Get all unique mentor types with their display names
    mentor_categories = []
    for mentor_type in mentor_types:
        # Format the mentor type for display (convert snake_case to Title Case)
        display_type = ' '.join(word.capitalize() for word in mentor_type.split('_'))
        
        # Get a count of mentors for this type
        mentor_count = Mentor.objects.filter(type=mentor_type).count()
        
        mentor_categories.append({
            'type': mentor_type,
            'display_name': display_type,
            'count': mentor_count
        })
    
    # Sort categories alphabetically
    mentor_categories.sort(key=lambda x: x['display_name'])
    
    # Count mentor sessions used today
    today = timezone.now().date()
    mentor_sessions_today = MentorChatUsage.objects.filter(
        user=request.user,
        date=today
    ).aggregate(total=models.Sum('messages_sent'))['total'] or 0
    
    # Calculate remaining sessions
    remaining_sessions = daily_limit - mentor_sessions_today
    if remaining_sessions < 0:
        remaining_sessions = 0
    
    return render(request, 'core/mentor.html', {
        'mentor_categories': mentor_categories,
        'is_premium': is_premium,
        'daily_limit': daily_limit,
        'mentor_sessions_today': mentor_sessions_today,
        'remaining_sessions': remaining_sessions
    })

@login_required
def mentor_list(request, mentor_type):
    """Display mentors of a specific type"""
    # Get all mentors of the requested type
    mentors = Mentor.objects.filter(type=mentor_type)
    
    # Get user profile information
    profile = request.user.profile
    is_premium = profile.is_premium
    
    # Filter out premium mentors if user is not premium
    if not is_premium:
        mentors = mentors.filter(is_premium=False)
    
    # Format the mentor type for display (convert snake_case to Title Case)
    display_type = ' '.join(word.capitalize() for word in mentor_type.split('_'))
    
    # Calculate remaining daily mentor messages
    daily_limit = 20 if is_premium else 5
    
    # Count mentor sessions used today
    today = timezone.now().date()
    mentor_sessions_today = MentorChatUsage.objects.filter(
        user=request.user,
        date=today
    ).aggregate(total=models.Sum('messages_sent'))['total'] or 0
    
    # Calculate remaining sessions
    remaining_sessions = daily_limit - mentor_sessions_today
    if remaining_sessions < 0:
        remaining_sessions = 0
    
    context = {
        'mentors': mentors,
        'mentor_type': display_type,
        'is_premium': is_premium,
        'daily_limit': daily_limit,
        'mentor_sessions_today': mentor_sessions_today,
        'remaining_sessions': remaining_sessions
    }
    
    return render(request, 'core/mentor_list.html', context)

@login_required
def chat_with_mentor(request, mentor_id):
    # Get the mentor
    mentor = get_object_or_404(Mentor, id=mentor_id)
    
    # Get or create usage record for today
    today = datetime.now().date()
    user = request.user
    
    chat_usage, created = MentorChatUsage.objects.get_or_create(
        user=user,
        mentor=mentor,
        date=today,
        defaults={'messages_sent': 0}
    )
    
    # Get chat history
    chat_history = MentorChat.objects.filter(user=user, mentor=mentor).order_by('timestamp')
    
    # Process form submission
    if request.method == 'POST':
        user_message = request.POST.get('message', '').strip()
        
        # Handle empty messages
        if not user_message:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Message cannot be empty'})
            else:
                messages.error(request, "Message cannot be empty.")
                return redirect('core:chat_with_mentor', mentor_id=mentor.id)
        
        # Check if user can send more messages
        if chat_usage.can_send_message():
            # Save user message
            MentorChat.objects.create(
                user=user,
                mentor=mentor,
                message=user_message,
                message_type='user'
            )
            
            # Generate mentor response
            mentor_response = generate_mentor_response(mentor, user_message, chat_history)
            
            # Save mentor response
            MentorChat.objects.create(
                user=user,
                mentor=mentor,
                message=mentor_response,
                message_type='mentor'
            )
            
            # Update usage counter
            chat_usage.messages_sent += 1
            chat_usage.save()
            
            # Refresh chat history
            chat_history = MentorChat.objects.filter(user=user, mentor=mentor).order_by('timestamp')
            
            # Return AJAX response if requested
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'response': mentor_response,
                    'remaining_messages': 20 if user.profile.is_premium else 5 - chat_usage.messages_sent,
                    'messages_sent': chat_usage.messages_sent
                })
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False, 
                    'error': "You've reached your daily message limit for this mentor. Try again tomorrow or upgrade to premium for more messages."
                })
            else:
                messages.warning(request, f"You've reached your daily message limit for this mentor. Try again tomorrow or upgrade to premium for more messages.")
    
    # Get user profile and premium status
    profile = user.profile
    is_premium = profile.is_premium
    
    # Calculate daily limit
    daily_limit = 20 if is_premium else 5
    
    # Count mentor sessions used today
    mentor_sessions_today = MentorChatUsage.objects.filter(
        user=user,
        date=today
    ).aggregate(total=models.Sum('messages_sent'))['total'] or 0
    
    # Calculate remaining sessions
    remaining_sessions = daily_limit - mentor_sessions_today
    if remaining_sessions < 0:
        remaining_sessions = 0
    
    context = {
        'mentor': mentor,
        'chat_history': chat_history,
        'chat_usage': chat_usage,
        'remaining_messages': 20 if user.profile.is_premium else 5 - chat_usage.messages_sent,
        'can_send_message': chat_usage.can_send_message(),
        'daily_limit': daily_limit,
        'mentor_sessions_today': mentor_sessions_today,
        'remaining_sessions': remaining_sessions
    }
    
    return render(request, 'core/mentor_chat.html', context)

@login_required
def chat_view(request, mentor_id):
    """Chat interface with a mentor"""
    mentor = get_object_or_404(Mentor, id=mentor_id)
    user = request.user
    today = timezone.now().date()
    
    # Check if this is a premium mentor and the user is not premium
    if mentor.is_premium and not user.profile.is_premium:
        messages.warning(request, "This is a premium mentor. Please upgrade to premium to chat with them.")
        return render(request, 'core/premium_required.html', {'mentor': mentor})
    
    # Get chat usage for today
    chat_usage = MentorChatUsage.get_for_user_mentor(user, mentor, today)
    
    # Get chat history
    chat_history = MentorChat.objects.filter(user=user, mentor=mentor).order_by('timestamp')
    
    # Handle new message submission
    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
        
        if message:
            # Check if user can send more messages today
            if chat_usage.can_send_message():
                # Save user message
                MentorChat.objects.create(
                    user=user,
                    mentor=mentor,
                    message=message,
                    message_type='user'
                )
                
                # Generate mentor response using GPT-4o-mini
                mentor_response = generate_mentor_response(mentor, message, chat_history)
                
                # Save mentor response
                MentorChat.objects.create(
                    user=user,
                    mentor=mentor,
                    message=mentor_response,
                    message_type='mentor'
                )
                
                # Update usage counter
                chat_usage.messages_sent += 1
                chat_usage.save()
                
                # Refresh chat history
                chat_history = MentorChat.objects.filter(user=user, mentor=mentor).order_by('timestamp')
            else:
                messages.warning(request, f"You've reached your daily message limit for this mentor. Try again tomorrow or upgrade to premium for more messages.")
    
    context = {
        'mentor': mentor,
        'chat_history': chat_history,
        'chat_usage': chat_usage,
        'remaining_messages': chat_usage.remaining_messages(),
        'can_send_message': chat_usage.can_send_message()
    }
    
    return render(request, 'core/mentor_chat.html', context)

def generate_mentor_response(mentor, user_message, chat_history=None):
    """Generate a response from the mentor based on their expertise and personality"""
    import os
    import openai
    import logging
    from django.conf import settings
    
    # Set up logging
    logger = logging.getLogger(__name__)
    
    # Get OpenAI API key from settings or environment variable
    api_key = getattr(settings, 'OPENAI_API_KEY', os.environ.get('OPENAI_API_KEY'))
    
    if not api_key:
        logger.warning("OpenAI API key is not configured. Using fallback responses.")
        return generate_fallback_response(mentor, user_message)
    
    # Set up OpenAI client
    client = openai.OpenAI(api_key=api_key)
    
    mentor_type = mentor.get_type_display()
    expertise = mentor.expertise
    
    # Create a prompt that captures the mentor's personality and expertise
    system_prompt = f"""You are {mentor.name}, a {mentor_type} with expertise in {expertise}. 
    {mentor.description}
    
    Keep your responses concise (100-150 words), professional, and helpful.
    If the question is outside your area of expertise, gently guide the conversation back to your specialty.
    If a premium mentor, provide more nuanced and detailed insights.
    
    Focus on providing actionable advice, not just general information."""
    
    # Create message list including history if available
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add chat history if provided (up to 10 most recent messages for context)
    if chat_history:
        # Get the 10 most recent messages (excluding the current one)
        recent_history = chat_history.order_by('-timestamp')[:10][::-1]  # Reverse to get chronological order
        
        for chat in recent_history:
            role = "user" if chat.message_type == "user" else "assistant"
            messages.append({"role": role, "content": chat.message})
    
    # Add the current user message
    messages.append({"role": "user", "content": user_message})
    
    try:
        # Make API call to OpenAI
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using GPT-4o-mini for efficient, quality responses
            messages=messages,
            temperature=0.7,
            max_tokens=200,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0.1
        )
        
        # Extract and return the response text
        return response.choices[0].message.content.strip()
    
    except openai.RateLimitError:
        logger.error("OpenAI API rate limit exceeded")
        return "I'm currently receiving a lot of questions. Please try again in a moment."
    
    except openai.APIError as e:
        logger.error(f"OpenAI API error: {str(e)}")
        return "I'm having trouble connecting to my knowledge base right now. Let's try again in a few minutes."
    
    except openai.APIConnectionError as e:
        logger.error(f"OpenAI API connection error: {str(e)}")
        return "I'm experiencing a temporary connection issue. Please try again shortly."
    
    except Exception as e:
        logger.error(f"Unexpected error generating response with OpenAI: {str(e)}")
        # Fallback to default responses if API call fails
        return generate_fallback_response(mentor, user_message)

def generate_fallback_response(mentor, user_message):
    """Fallback method to generate responses when OpenAI API is unavailable"""
    mentor_type = mentor.get_type_display()
    expertise = mentor.expertise
    
    # Simple response based on mentor type
    responses = {
        'Career Coach': f"As a career coach specializing in {expertise}, I would suggest focusing on your professional development goals. What specific career challenges are you facing right now?",
        'Financial Advisor': f"From a financial perspective considering my expertise in {expertise}, I'd recommend evaluating your long-term financial goals. Could you tell me more about your financial situation?",
        'Relationship Counselor': f"In relationships, communication is key. With my background in {expertise}, I can help you navigate this situation. Can you share more details about what you're experiencing?",
        'Time Management Expert': f"Time management is about prioritization. Given my focus on {expertise}, I'd recommend starting with a clear schedule. What specific time challenges are you facing?",
        'Educational Consultant': f"Education is a lifelong journey. With my expertise in {expertise}, I can guide your learning path. What are your educational goals?",
        'Health & Wellness Coach': f"Wellness requires balance in all aspects of life. Based on my knowledge of {expertise}, I'd suggest starting with small, sustainable changes. What specific health concerns do you have?",
        'Life Coach': f"Life's challenges often require perspective. Drawing from my experience in {expertise}, I believe you have the inner resources to overcome this. What specific situation are you dealing with?",
        'Astrology Expert': f"The planetary alignments can offer insights into your situation. With my focus on {expertise}, I can interpret these cosmic influences. What's your birth date and time?",
        'Creative Thinking Coach': f"Creative blocks are normal parts of the process. Using techniques from {expertise}, we can work through them together. What creative project are you working on?"
    }
    
    # Default response if mentor type not found
    return responses.get(mentor_type, f"I'm here to help with {expertise}. How can I assist you today?")

@login_required
def scenarios_view(request):
    # Get all scenarios
    all_scenarios = Scenario.objects.all()
    
    # If user is logged in, filter by level and track completed scenarios
    if request.user.is_authenticated:
        user_level = request.user.profile.level
        scenarios = all_scenarios.filter(unlocked_at_level__lte=user_level)
        
        # Get user progress for these scenarios
        completed_scenarios = set(
            UserScenarioProgress.objects.filter(
                user=request.user, 
                completed=True
            ).values_list('scenario_id', flat=True)
        )
        
        # Get recent scenarios for the user
        recent_scenarios = []
        
        # Get the most recent scenarios (both completed and not)
        user_progress = UserScenarioProgress.objects.filter(
            user=request.user
        ).order_by('-completed_at')[:4]
        
        for progress in user_progress:
            scenario = progress.scenario
            scenario.is_completed = progress.completed
            recent_scenarios.append(scenario)
        
        # If we don't have 4 scenarios yet, add some random ones
        if len(recent_scenarios) < 4:
            remaining = 4 - len(recent_scenarios)
            existing_ids = [s.id for s in recent_scenarios]
            random_scenarios = Scenario.objects.exclude(
                id__in=existing_ids
            ).order_by('?')[:remaining]
            
            for scenario in random_scenarios:
                scenario.is_completed = scenario.id in completed_scenarios
                recent_scenarios.append(scenario)
    else:
        # For anonymous users, only show level 1 scenarios
        scenarios = all_scenarios.filter(unlocked_at_level=1)
        completed_scenarios = set()
        recent_scenarios = Scenario.objects.filter(unlocked_at_level=1).order_by('?')[:4]
        for scenario in recent_scenarios:
            scenario.is_completed = False
    
    # Group scenarios by category
    categories = {}
    for scenario in scenarios:
        category = scenario.get_category_display()
        if category not in categories:
            categories[category] = []
        
        # Add completion status
        scenario.is_completed = scenario.id in completed_scenarios
        categories[category].append(scenario)
    
    context = {
        'categories': categories,
        'recent_scenarios': recent_scenarios,
    }
    return render(request, 'core/scenarios.html', context)

@login_required
@log_request_performance
@cache_page(60 * 5)  # Cache this view for 5 minutes
def generated_scenarios(request):
    """View for displaying user's generated scenarios"""
    # Get all scenarios that the user has interacted with
    try:
        if request.user.is_authenticated:
            # Cache key for this user's generated scenarios
            cache_key = f"user_{request.user.id}_generated_scenarios"
            cached_data = cache.get(cache_key)
            
            if cached_data is not None:
                scenarios = cached_data
            else:
                # Get all user progress records with optimized query
                user_progress = UserScenarioProgress.objects.filter(
                    user=request.user
                ).select_related(
                    'scenario', 'selected_option'
                ).prefetch_related(
                    'scenario__options'
                ).order_by('-last_attempt_date')
                
                logger.info(f"User {request.user.username} has {user_progress.count()} progress records.")
                
                # Get IDs of completed scenarios - use a set for O(1) lookup
                completed_scenario_ids = set(
                    user_progress.filter(completed=True).values_list('scenario_id', flat=True)
                )
                
                # Pre-compute scenarios the user has interacted with but not completed
                scenarios = []
                for progress in user_progress:
                    # Include all scenarios that are not in completed_scenario_ids or not completed
                    if progress.scenario.id not in completed_scenario_ids or not progress.completed:
                        scenario = progress.scenario
                        scenario.is_completed = False
                        scenario.progress = progress
                        scenarios.append(scenario)
                
                # Cache the result
                cache.set(cache_key, scenarios, 300)  # 5 minutes
        else:
            # For anonymous users, redirect to login
            messages.warning(request, "Please log in to view your generated scenarios.")
            return redirect('core:login')
        
        context = {
            'generated_scenarios': True,
            'completed_scenarios': False,
            'recent_scenarios': scenarios,
            'page_title': 'Generated Scenarios'
        }
        return render(request, 'core/scenarios.html', context)
    except Exception as e:
        logger.error(f"Error in generated_scenarios view: {str(e)}")
        messages.error(request, "An error occurred while loading your generated scenarios. Please try again.")
        return render(request, 'core/scenarios.html', {
            'generated_scenarios': True,
            'completed_scenarios': False,
            'recent_scenarios': [],
            'page_title': 'Generated Scenarios',
            'error': str(e)
        })

@login_required
@log_request_performance
@cache_page(60 * 5)  # Cache this view for 5 minutes
def completed_scenarios(request):
    """View for displaying user's completed scenarios"""
    try:
        if request.user.is_authenticated:
            # Cache key for this user's completed scenarios
            cache_key = f"user_{request.user.id}_completed_scenarios"
            cached_data = cache.get(cache_key)
            
            if cached_data is not None:
                completed_scenarios = cached_data
            else:
                # Get user progress for completed scenarios with optimized query
                user_progress = UserScenarioProgress.objects.filter(
                    user=request.user,
                    completed=True
                ).select_related(
                    'scenario', 'selected_option'
                ).prefetch_related(
                    'scenario__options'
                ).order_by('-completed_at')
                
                # Pre-compute the scenario objects with completion status
                completed_scenarios = []
                for progress in user_progress:
                    scenario = progress.scenario
                    scenario.is_completed = True
                    scenario.progress = progress
                    completed_scenarios.append(scenario)
                
                # Cache the result
                cache.set(cache_key, completed_scenarios, 300)  # 5 minutes
                
            logger.info(f"User {request.user.username} has {len(completed_scenarios)} completed scenarios.")
        else:
            # For anonymous users, redirect to login
            messages.warning(request, "Please log in to view your completed scenarios.")
            return redirect('core:login')
        
        context = {
            'completed_scenarios': True,
            'generated_scenarios': False,
            'recent_scenarios': completed_scenarios,
            'page_title': 'Completed Scenarios'
        }
        return render(request, 'core/scenarios.html', context)
    except Exception as e:
        logger.error(f"Error in completed_scenarios view: {str(e)}")
        messages.error(request, "An error occurred while loading your completed scenarios. Please try again.")
        return render(request, 'core/scenarios.html', {
            'completed_scenarios': True,
            'generated_scenarios': False,
            'recent_scenarios': [],
            'page_title': 'Completed Scenarios',
            'error': str(e)
        })

def home(request):
    if request.method == 'POST':
        # Redirect to dedicated feedback handling functions
        return visitor_feedback(request)
    
    return render(request, 'core/home.html')

def visitor_feedback(request):
    """Separate function to handle feedback from anonymous visitors"""
    if request.method != 'POST':
        return redirect('core:home')
        
    # Process feedback form
    name = request.POST.get('name')
    email = request.POST.get('email')
    feedback_type = request.POST.get('feedback_type')
    message = request.POST.get('message')
    
    # Create a support issue from the feedback
    if name and email and feedback_type and message:
        # Create a user account if it doesn't exist
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Create a temporary user based on the email
            username = email.split('@')[0]
            # Ensure unique username
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
                
            # Create user with random password
            import random
            import string
            temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            user = User.objects.create_user(
                username=username,
                email=email,
                password=temp_password
            )
            
        # Create a support issue
        issue = SupportIssue.objects.create(
            user=user,
            title=f"Feedback: {feedback_type.capitalize()}",
            description=message,
            priority='medium',
            issue_type='feedback'
        )
        
        # Add a comment with the user's name if different from username
        if name != user.username:
            IssueComment.objects.create(
                issue=issue,
                user=user,
                comment=f"Submitted by: {name}",
                is_staff_comment=False
            )
        
        messages.success(request, "Thank you for your feedback! We'll review it and get back to you if needed.")
    else:
        messages.error(request, "Please fill out all fields in the feedback form.")
    
    return redirect('core:home')

def item_list(request):
    items = Item.objects.all()
    context = {
        'items': items
    }
    return render(request, 'core/item_list.html', context)

@csrf_protect 
@never_cache
def login_view(request):
    """
    Custom login view using email authentication
    """
    # Redirect authenticated users to dashboard
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    # We don't need to check for social auth errors here anymore
    # The social_auth_error view will handle it
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        logger.info(f"Login attempt for email: {email}")
        
        if email and password:
            try:
                # Try to get user by email
                try:
                    username = User.objects.get(email=email).username
                except User.DoesNotExist:
                    username = email
                except User.MultipleObjectsReturned:
                    # Handle multiple users with same email - use the most recently created one
                    logger.warning(f"Multiple users found with same email: {email}")
                    username = User.objects.filter(email=email).order_by('-date_joined').first().username
                
                # Attempt to authenticate with username (which could be the email)
                user = authenticate(username=username, password=password)
                if user is not None:
                    login(request, user)
                    logger.info(f"Successful login for user: {user.username} ({user.email})")
                    messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
                    
                    # Handle next parameter for redirects
                    next_url = request.POST.get('next') or request.GET.get('next')
                    if next_url:
                        return redirect(next_url)
                    return redirect('core:dashboard')
                else:
                    logger.warning(f"Authentication failed for email: {email}")
                    form.add_error(None, "Invalid email or password.")
            except Exception as e:
                logger.error(f"Error during login: {e}")
                form.add_error(None, "An error occurred during login. Please try again.")
    else:
        form = AuthenticationForm()
    
    return render(request, 'core/login.html', {'form': form})

def register_view(request):
    # Redirect authenticated users to dashboard
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                # Check if email is already in use (extra check including social auth accounts)
                email = form.cleaned_data.get('email')
                username = form.cleaned_data.get('username')
                
                # Check username uniqueness
                if User.objects.filter(username=username).exists():
                    form.add_error('username', "This username is already taken. Please choose a different username.")
                    return render(request, 'core/register.html', {'form': form})
                
                # Check email uniqueness
                if email and User.objects.filter(email=email).exists():
                    form.add_error('email', "This email address is already registered. Please use a different email or reset your password.")
                    return render(request, 'core/register.html', {'form': form})
                
                # Create user if both username and email are unique
                user = form.save()
                backend = 'django.contrib.auth.backends.ModelBackend'
                
                # Log the successful registration
                logger.info(f"New user registered: {username} ({email})")
                
                # Send welcome email
                from .utils import send_welcome_email
                try:
                    send_welcome_email(user)
                    logger.info(f"Welcome email sent to {email}")
                except Exception as e:
                    logger.error(f"Failed to send welcome email: {str(e)}")
                
                # Auto-login the user after registration
                login(request, user, backend=backend)
                
                # Redirect to dashboard with new_user flag to trigger tour
                return redirect(reverse('core:dashboard') + '?new_user=true')
            except Exception as e:
                logger.error(f"Error during registration: {e}")
                form.add_error(None, "An error occurred during registration. Please try again.")
        else:
            # Form validation errors will be displayed in the template
            logger.warning(f"Registration form validation failed: {form.errors}")
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'core/register.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully!")
    return redirect('core:home')
def chrome_devtools_json(request):
    # Return a JSON response with the required data
    data = {'key': 'value'}
    return HttpResponse(json.dumps(data), content_type='application/json')
def password_reset_request(request):
    """View for handling password reset requests"""
    try:
        if request.method == "POST":
            email = request.POST.get("email", "")
            associated_users = User.objects.filter(email=email)
            # logging.info(f"Password reset request for email: {email}")
            if not email:
                logging.warning("Password reset request received with empty email.")
                messages.error(request, "Please enter a valid email address.")
                return render(request, 'core/password_reset.html')
            if not associated_users:
                # logging.info(f"No users found with email: {email}")
                messages.info(request, "If an account with that email exists, a password reset link will be sent.")
                return redirect('core:password_reset_done')
            if associated_users.exists():
                # Send password reset emails
                # logging.info(f"Password reset requested for email: {email}")
                for user in associated_users:
                    # Generate a password reset token
                    token_generator = default_token_generator
                    uid = urlsafe_base64_encode(force_bytes(user.pk))
                    token = token_generator.make_token(user)
                    # logging.info(f"Generated token for user {user.email}: {token}")
                    # Build reset URL
                    current_site = get_current_site(request)
                    reset_url = f"{request.scheme}://{current_site.domain}{reverse('core:password_reset_confirm', args=[uid, token])}"
                    logging.info(f"Generated password reset URL: {reset_url}")
                    # Create email subject and body
                    subject = "Password Reset Request for DesiQ"
                    
                    # Check if we're using Gmail API (which supports HTML)
                    use_gmail_api = getattr(settings, 'USE_GMAIL_API', False)
                    # logging.info(f"Gmail API enabled: {use_gmail_api}")
                    if use_gmail_api:
                        # HTML email body
                        # logging.info("Using HTML email template for password reset")
                        email_body = render_to_string('core/password_reset_email.html', {
                            'user': user,
                            'reset_url': reset_url,
                            'domain': current_site.domain,
                            'uid': uid,
                            'token': token,
                            'protocol': request.scheme,
                        })
                    else:
                        # Plain text email body
                        # logging.info("Using plain text email template for password reset")
                        email_body = render_to_string('core/password_reset_email.txt', {
                            'user': user,
                            'reset_url': reset_url,
                            'domain': current_site.domain,
                            'uid': uid,
                            'token': token,
                            'protocol': request.scheme,
                        })
                    
                    # Send email
                    try:
                        # logging.info(f"Sending password reset email to {user.email}")
                        send_mail(subject=subject, message=email_body, from_email=os.environ.get('DEFAULT_FROM_EMAIL'), recipient_list=[user.email], fail_silently=False)
                        logging.info(f"default_from_email: {settings.DEFAULT_FROM_EMAIL}")
                        logging.info("Password reset email sent successfully")
                    except Exception as e:
                        # Log the error but don't expose it to the user
                        # logging.error(f"Error sending password reset email: {e}")
                        messages.error(request, "An error occurred while sending the password reset email. Please try again later.")
                        return redirect('core/password_reset.html')
                
                return redirect('core:password_reset_done')
            
            # Even if no user found, redirect to done page to prevent email enumeration
            return redirect('core:password_reset_done')
    except Exception as e:
        # Log the error but don't expose it to the user
        # logging.error(f"Error processing password reset request: {e}")
        # messages.error(request, "An error occurred while processing your request. Please try again later.")
        return render(request, 'core/password_reset.html', {'error': "An error occurred while processing your request. Please try again later."})
    
    return render(request, 'core/password_reset.html')

@login_required
def scenario_detail(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    user = request.user
    today = timezone.now().date()
    
    # Check if the user's level is high enough to access this scenario
    if user.profile.level < scenario.unlocked_at_level:
        messages.warning(request, f"This scenario is locked until you reach level {scenario.unlocked_at_level}.")
        return redirect('core:scenarios')
    
    # Check if this is a daily challenge
    daily_challenge = DailyChallenge.objects.filter(
        user=user,
        scenario=scenario,
        date_created=today
    ).first()
    
    # Get or create user progress for this scenario
    progress, created = UserScenarioProgress.objects.get_or_create(
        user=user,
        scenario=scenario
    )
    
    # Check daily attempt limits
    daily_tracker = DailyUsageTracker.get_for_user(user, today)
    
    # Check if the user has already attempted this scenario twice today
    if progress.last_attempt_date == today and progress.attempts >= 2:
        messages.warning(request, "You've already attempted this scenario twice today. Try again tomorrow.")
        return redirect('core:scenarios')
    
    # Check if the user has reached their daily scenario attempt limit
    # Only check this if it's NOT a daily challenge
    if not daily_challenge and not daily_tracker.can_attempt_scenario():
        max_attempts = 5 if user.profile.is_premium else 2
        messages.warning(request, f"You've reached your daily limit of {max_attempts} scenario attempts. Try again tomorrow or upgrade to premium.")
        return redirect('core:scenarios')
    
    # If this is a daily challenge and it's already been completed, redirect to results
    if daily_challenge and progress.completed:
        messages.info(request, "You've already completed this daily challenge.")
        return redirect('core:scenario_result', scenario_id=scenario.id)
    
    # Get options for this scenario
    options = scenario.options.all()
    
    if request.method == 'POST':
        option_id = request.POST.get('option')
        if option_id:
            selected_option = get_object_or_404(ScenarioOption, id=option_id)
            
            # Update user progress
            progress.completed = True
            progress.selected_option = selected_option
            progress.completed_at = timezone.now()
            progress.attempts += 1
            progress.last_attempt_date = today
            progress.save()
            
            # Update daily tracker only if this is NOT a daily challenge
            if not daily_challenge:
                daily_tracker.scenarios_attempted += 1
                daily_tracker.save()
            
            # Update user profile with points
            profile = user.profile
            profile.xp_points += scenario.xp_reward
            profile.rationality_score += selected_option.rationality_points
            profile.decisiveness_score += selected_option.decisiveness_points
            profile.empathy_score += selected_option.empathy_points
            profile.clarity_score += selected_option.clarity_points
            
            # Level up if needed (simple level system: 100 XP per level)
            new_level = (profile.xp_points // 100) + 1
            if new_level > profile.level:
                profile.level = new_level
                messages.success(request, f"Congratulations! You've reached level {new_level}!")
            
            profile.save()
            
            # If this is a daily challenge, mark it as completed
            if daily_challenge:
                daily_challenge.completed = True
                daily_challenge.completed_at = timezone.now()
                daily_challenge.save()
                messages.success(request, f"Daily challenge completed! You've earned {scenario.xp_reward} XP!")
            else:
                messages.success(request, f"You've completed the scenario and earned {scenario.xp_reward} XP!")
            
            # Generate next scenario if this option has no linked scenario yet
            if selected_option.next_scenario is None and request.POST.get('continue_story') == 'true':
                try:
                    from .utils import generate_scenario_with_openai, create_scenario_from_data
                    # Generate a related scenario based on the selected option
                    scenario_data = generate_scenario_with_openai(
                        category=scenario.category, 
                        previous_option=selected_option
                    )
                    next_scenario = create_scenario_from_data(scenario_data, selected_option)
                    messages.info(request, "A follow-up scenario has been generated based on your choice!")
                except Exception as e:
                    print(f"Error generating follow-up scenario: {str(e)}")
            
            return redirect('core:scenario_result', scenario_id=scenario.id)
    else:
        # Track attempt if viewing the scenario
        if not progress.completed:
            progress.attempts += 1
            progress.last_attempt_date = today
            progress.save()
            
            # Update daily tracker only if this is NOT a daily challenge
            if not daily_challenge:
                daily_tracker.scenarios_attempted += 1
                daily_tracker.save()
    
    context = {
        'scenario': scenario,
        'options': options,
        'progress': progress,
        'is_daily_challenge': daily_challenge is not None
    }
    return render(request, 'core/scenario_detail.html', context)

@login_required
def scenario_result(request, scenario_id):
    scenario = get_object_or_404(Scenario, id=scenario_id)
    try:
        progress = UserScenarioProgress.objects.get(user=request.user, scenario=scenario)
        if not progress.completed:
            messages.warning(request, "You haven't completed this scenario yet.")
            return redirect('core:scenario_detail', scenario_id=scenario.id)
        
        # Calculate total score
        selected_option = progress.selected_option
        total_score = 0
        if selected_option:
            total_score = (
                selected_option.rationality_points +
                selected_option.decisiveness_points +
                selected_option.empathy_points +
                selected_option.clarity_points
            )
        
        # Generate improvement suggestions based on scores
        suggestions = []
        if selected_option.rationality_points < 5:
            suggestions.append("Consider gathering more information before making decisions.")
        if selected_option.decisiveness_points < 5:
            suggestions.append("Work on making decisions more quickly and confidently.")
        if selected_option.empathy_points < 5:
            suggestions.append("Try to consider how your decisions affect others.")
        if selected_option.clarity_points < 5:
            suggestions.append("Focus on understanding the full context before deciding.")
        
        # Check if there's a follow-up scenario
        next_scenario = None
        if selected_option and selected_option.next_scenario:
            next_scenario = selected_option.next_scenario
        
        # Generate share URL (simplified version)
        share_url = request.build_absolute_uri()
        
        context = {
            'scenario': scenario,
            'progress': progress,
            'selected_option': selected_option,
            'total_score': total_score,
            'suggestions': suggestions,
            'next_scenario': next_scenario,
            'share_url': share_url
        }
        return render(request, 'core/scenario_result.html', context)
    
    except UserScenarioProgress.DoesNotExist:
        messages.warning(request, "You haven't started this scenario yet.")
        return redirect('core:scenario_detail', scenario_id=scenario.id)

@login_required
@log_request_performance
def dashboard_view(request):
    user = request.user
    profile = user.profile
    
    # Get completed scenarios for this user - optimize with select_related
    completed_scenarios = UserScenarioProgress.objects.filter(
        user=user,
        completed=True
    ).select_related('scenario', 'selected_option').order_by('-completed_at')
    
    # Count scenarios completed today
    today = timezone.now().date()
    scenarios_completed_today = completed_scenarios.filter(
        completed_at__date=today
    ).count()
    
    # Get daily usage tracker for today
    daily_tracker = DailyUsageTracker.get_for_user(user, today)
    
    # Determine user type (free or premium)
    is_premium = profile.is_premium
    
    # Set limits based on user type
    max_scenarios_per_day = 5 if is_premium else 2
    max_mentor_sessions_per_day = 20 if is_premium else 5
    max_cards = 5 if is_premium else 3
    
    # Get daily challenges for today - optimize with select_related
    daily_challenges = DailyChallenge.objects.filter(
        user=user,
        date_created=today
    ).select_related('scenario')
    
    # If no challenges exist for today, generate them
    if not daily_challenges.exists():
        from .utils import generate_daily_challenges_for_user
        num_challenges = 3 if is_premium else 1
        daily_challenges = generate_daily_challenges_for_user(user, num_challenges)
    
    # Format challenges for the template - precompute values to avoid lazy loading in templates
    challenge_data = []
    for challenge in daily_challenges:
        challenge_data.append({
            'id': challenge.id,
            'name': challenge.scenario.title,
            'xp_reward': challenge.scenario.xp_reward,
            'completed': challenge.completed,
            'locked': challenge.is_locked and not challenge.completed,
            'scenario_id': challenge.scenario.id
        })
    
    # Recent decisions data - optimize by adding limit directly to the query
    recent_decisions = []
    for i, scenario in enumerate(completed_scenarios[:max_cards]):
        if scenario.selected_option:
            recent_decisions.append({
                'title': scenario.scenario.title,
                'date': scenario.completed_at,
                'score': scenario.selected_option.rationality_points + 
                         scenario.selected_option.decisiveness_points +
                         scenario.selected_option.empathy_points +
                         scenario.selected_option.clarity_points
            })
    
    # Calculate XP progress percentage for current level
    current_level_xp = profile.level * 100
    next_level_xp = (profile.level + 1) * 100
    xp_for_current_level = profile.xp_points - current_level_xp
    xp_needed_for_next_level = next_level_xp - current_level_xp
    xp_progress_percentage = int((xp_for_current_level / xp_needed_for_next_level) * 100) if xp_needed_for_next_level > 0 else 0
    
    # Query for mentor sessions today - do this only if needed
    mentor_sessions_today = 0
    if hasattr(request, '_mentor_sessions_counted'):
        mentor_sessions_today = request._mentor_sessions_counted
    else:
        try:
            # Get mentor sessions for today - only count, don't fetch objects
            mentor_sessions_today = MentorChatUsage.objects.filter(
                user=user, 
                date=today
            ).aggregate(total=Count('messages_sent'))['total'] or 0
            request._mentor_sessions_counted = mentor_sessions_today
        except Exception:
            mentor_sessions_today = 0
    
    context = {
        'user': user,
        'profile': profile,
        'rationality_score': profile.rationality_score,
        'decisiveness_score': profile.decisiveness_score,
        'scenarios_completed': completed_scenarios.count(),
        'streak': profile.daily_streak,
        'daily_challenges_completed': sum(1 for c in challenge_data if c['completed']),
        'daily_challenges_total': len(challenge_data),
        'daily_challenges': challenge_data,
        'scenarios_generated': daily_tracker.scenarios_generated,
        'scenarios_today': scenarios_completed_today,
        'max_scenarios_per_day': max_scenarios_per_day,
        'mentor_sessions_today': mentor_sessions_today,
        'max_mentor_sessions_per_day': max_mentor_sessions_per_day,
        'user_decisions': recent_decisions,
        'xp': profile.xp_points,
        'level': profile.level,
        'xp_progress_percentage': xp_progress_percentage,
        'is_premium': is_premium
    }
    
    return render(request, 'core/dashboard.html', context)

@login_required
def generate_scenario(request, category):
    user = request.user
    today = timezone.now().date()
    
    # Map UI categories to model categories
    category_mapping = {
        'career': 'career',
        'financial': 'finance',
        'relationship': 'relationships',
        'time': 'time_management',
        'educational': 'education',
        'health': 'health',
        'ethics': 'ethics',
        'other': 'other'
    }
    
    # Default to 'other' if category not found
    model_category = category_mapping.get(category.lower(), category.lower())
    
    # Get daily usage tracker
    daily_tracker = DailyUsageTracker.get_for_user(user, today)
    
    # Check if user can generate more scenarios today
    if not daily_tracker.can_generate_scenario():
        max_scenarios = 5 if user.profile.is_premium else 2
        messages.warning(request, f"You've reached your daily limit of {max_scenarios} generated scenarios. Upgrade to premium for more or try again tomorrow.")
        return redirect('core:scenarios')
    
    # Check if user level is high enough for this category
    level_requirements = {
        'career': 1,
        'finance': 2,
        'relationships': 3,
        'time_management': 4,
        'education': 5,
        'health': 6,
        'ethics': 7,
        'other': 1
    }
    
    required_level = level_requirements.get(model_category, 1)
    if user.profile.level < required_level:
        messages.warning(request, f"You need to reach level {required_level} to generate {model_category.capitalize()} scenarios.")
        return redirect('core:scenarios')
    
    try:
        # Generate the scenario
        from .utils import generate_scenario_with_openai, create_scenario_from_data
        scenario_data = generate_scenario_with_openai(model_category)
        
        # Ensure the scenario is assigned the correct level requirement
        scenario_data['unlocked_at_level'] = required_level
        
        # Create the scenario
        scenario = create_scenario_from_data(scenario_data)
        
        # Update daily tracker
        daily_tracker.scenarios_generated += 1
        daily_tracker.save()
        
        messages.success(request, f"New {scenario.get_category_display()} scenario created successfully!")
        
        # Redirect to the scenario detail page
        return redirect('core:scenario_detail', scenario_id=scenario.id)
        
    except Exception as e:
        print(f"Error generating scenario: {str(e)}")
        messages.error(request, "There was an error generating your scenario. Please try again.")
        return redirect('core:scenarios')

def generate_test_questions(test):
    """Generate test questions using GPT-4o-mini"""
    import openai
    import json
    import os
    from django.conf import settings
    import uuid
    
    # Set up OpenAI API
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    
    # Prepare prompt based on test type
    prompt = f"""Generate {test.question_count} multiple-choice questions for a {test.title} personality test.
    Each question should have 4 options (A, B, C, D).
    Return the response as a JSON array with each question having the following structure:
    {{
        "id": "unique_id",
        "question": "Question text",
        "options": [
            "Option A",
            "Option B",
            "Option C",
            "Option D"
        ]
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a personality test creator specializing in creating engaging and insightful questions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        )
        
        # Extract and parse the JSON response
        content = response.choices[0].message.content
        # Find JSON content between ```json and ``` if present
        import re
        json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        
        questions_data = json.loads(content)
        
        # Ensure each question has a unique ID
        for question in questions_data:
            if 'id' not in question or not question['id']:
                question['id'] = str(uuid.uuid4())
        
        return questions_data
        
    except Exception as e:
        # Fallback to static questions if API fails
        print(f"Error generating questions: {str(e)}")
        print(test.title)
        if test.title == "Cognitive Bias Test":
            fallback_questions = [
                    {
                        "id": str(uuid.uuid4()),
                        "question": "When faced with a stressful situation, how do you usually respond?",
                        "options": [
                            "A. I stay calm and try to think logically.",
                            "B. I talk to someone to release stress.",
                            "C. I tend to avoid the situation altogether.",
                            "D. I get anxious and overthink everything."
                        ]
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "question": "How do you typically make decisions?",
                        "options": [
                            "A. Based on gut feeling.",
                            "B. After careful analysis of facts.",
                            "C. By asking others for advice.",
                            "D. I struggle to make decisions."
                        ]
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "question": "In group settings, you are most likely to:",
                        "options": [
                            "A. Take the lead and guide others.",
                            "B. Observe and contribute when needed.",
                            "C. Blend in and follow others' lead.",
                            "D. Avoid group settings if possible."
                        ]
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "question": "How do you handle feedback?",
                        "options": [
                            "A. I welcome it and use it to grow.",
                            "B. I appreciate it but take it with caution.",
                            "C. I often feel defensive at first.",
                            "D. I find it difficult to accept criticism."
                        ]
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "question": "What best describes your work style?",
                        "options": [
                            "A. Organized and methodical.",
                            "B. Flexible and adaptive.",
                            "C. Energetic but easily distracted.",
                            "D. Cautious and reserved."
                        ]
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "question": "Which of the following do you value most?",
                        "options": [
                            "A. Achievement and success.",
                            "B. Harmony and relationships.",
                            "C. Freedom and creativity.",
                            "D. Stability and security."
                        ]
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "question": "When starting a new task, you usually:",
                        "options": [
                            "A. Plan every detail before beginning.",
                            "B. Dive in and figure it out as you go.",
                            "C. Wait for clear instructions.",
                            "D. Procrastinate until the last moment."
                        ]
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "question": "How do you recharge after a long day?",
                        "options": [
                            "A. Spending time alone.",
                            "B. Talking with friends or family.",
                            "C. Engaging in a hobby or activity.",
                            "D. Sleeping or doing nothing."
                        ]
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "question": "How do you typically approach conflict?",
                        "options": [
                            "A. I try to resolve it quickly and fairly.",
                            "B. I avoid it whenever possible.",
                            "C. I confront the issue head-on.",
                            "D. I let it go unless it escalates."
                        ]
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "question": "What motivates you the most?",
                        "options": [
                            "A. Recognition and praise.",
                            "B. Personal growth and learning.",
                            "C. Helping others and making a difference.",
                            "D. Financial security and rewards."
                        ]
                    }
                ]
        elif test.title == "Decision Making Style Assessment":
            fallback_questions = [
                        {
                            "id": str(uuid.uuid4()),
                            "question": "When faced with a tough decision, what's your first reaction?",
                            "options": [
                                "A. I analyze the pros and cons.",
                                "B. I ask someone I trust for advice.",
                                "C. I go with my gut feeling.",
                                "D. I avoid deciding until necessary."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do you make everyday decisions like what to eat or wear?",
                            "options": [
                                "A. I plan in advance.",
                                "B. I decide based on how I feel in the moment.",
                                "C. I go with whatever is fastest.",
                                "D. I ask others for input."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "Do you consider long-term consequences when making decisions?",
                            "options": [
                                "A. Always – it's essential.",
                                "B. Sometimes, if the decision is big.",
                                "C. Rarely – I focus on the short-term.",
                                "D. I let things play out on their own."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "When under pressure, how do you make decisions?",
                            "options": [
                                "A. I stay calm and follow a process.",
                                "B. I trust my instincts more.",
                                "C. I rush and hope for the best.",
                                "D. I freeze and try to delay."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do you handle regret after making a decision?",
                            "options": [
                                "A. I learn from it and move on.",
                                "B. I dwell on it and feel anxious.",
                                "C. I justify it to feel better.",
                                "D. I try to reverse the decision if possible."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "Do you prefer structure or flexibility in your decision-making?",
                            "options": [
                                "A. Structure – I like a clear method.",
                                "B. Flexibility – I adjust as I go.",
                                "C. A mix of both.",
                                "D. I don't really think about it."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do emotions impact your decisions?",
                            "options": [
                                "A. I try to keep them out of it.",
                                "B. I acknowledge them but don't let them rule me.",
                                "C. I often decide based on how I feel.",
                                "D. I struggle to separate feelings from facts."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "Do you tend to seek out multiple options before deciding?",
                            "options": [
                                "A. Yes – I want to be thorough.",
                                "B. Sometimes – if time permits.",
                                "C. No – too many options are overwhelming.",
                                "D. I stick to familiar choices."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How often do you second-guess your decisions?",
                            "options": [
                                "A. Rarely – I trust myself.",
                                "B. Sometimes – it depends on the outcome.",
                                "C. Often – I worry I made the wrong choice.",
                                "D. Always – I overanalyze everything."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "If someone disagrees with your decision, how do you react?",
                            "options": [
                                "A. I listen and reconsider if necessary.",
                                "B. I defend my choice confidently.",
                                "C. I doubt myself and get confused.",
                                "D. I ignore them and move on."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do deadlines affect your decision-making?",
                            "options": [
                                "A. I make quicker but thoughtful decisions.",
                                "B. I panic and often choose poorly.",
                                "C. I perform better under pressure.",
                                "D. I delay and feel overwhelmed."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How open are you to changing your decision later?",
                            "options": [
                                "A. Very open – flexibility is key.",
                                "B. Only if new facts emerge.",
                                "C. I avoid changing once I decide.",
                                "D. I often change my mind even without new info."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "Which statement best describes your decision-making goal?",
                            "options": [
                                "A. I want to make the most logical choice.",
                                "B. I want to make the choice that feels right.",
                                "C. I want others to approve of my choice.",
                                "D. I want to avoid responsibility for bad choices."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "Do you often rely on past experiences to guide decisions?",
                            "options": [
                                "A. Always – past patterns help a lot.",
                                "B. Sometimes – if the situation is familiar.",
                                "C. Rarely – each case is different.",
                                "D. I don't think about the past when deciding."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "When collaborating with others, how do you handle group decisions?",
                            "options": [
                                "A. I advocate for my views confidently.",
                                "B. I seek consensus even if it takes time.",
                                "C. I go along with the majority.",
                                "D. I prefer deciding things alone."
                            ]
                        }
                    ]
        elif test.title == "Emotional Intelligence Assessment":
            fallback_questions = [
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do you usually respond when someone criticizes you?",
                            "options": [
                                "A. I reflect on it before reacting.",
                                "B. I get defensive.",
                                "C. I ignore them.",
                                "D. I immediately feel hurt and withdraw."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "You're feeling overwhelmed at work. What's your first step?",
                            "options": [
                                "A. I take a break and refocus.",
                                "B. I talk to someone about it.",
                                "C. I try to push through silently.",
                                "D. I vent or get irritated."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do you handle someone else's anger directed at you?",
                            "options": [
                                "A. I stay calm and try to understand.",
                                "B. I get angry in return.",
                                "C. I shut down emotionally.",
                                "D. I walk away immediately."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do you recognize when you're feeling stressed?",
                            "options": [
                                "A. I notice changes in my behavior and mood.",
                                "B. Others usually point it out.",
                                "C. I don't notice until it's too late.",
                                "D. I avoid thinking about it."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do you typically comfort a friend in distress?",
                            "options": [
                                "A. I listen and empathize.",
                                "B. I try to give them advice.",
                                "C. I distract them with humor.",
                                "D. I change the subject to avoid awkwardness."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How easy is it for you to express your emotions?",
                            "options": [
                                "A. Very easy – I'm emotionally open.",
                                "B. It depends on who I'm with.",
                                "C. I find it difficult.",
                                "D. I avoid it altogether."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "Someone in your team is upset. What do you do?",
                            "options": [
                                "A. Ask if they'd like to talk about it.",
                                "B. Pretend not to notice.",
                                "C. Tell them to cheer up.",
                                "D. Let someone else handle it."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "You receive emotional feedback that you disagree with. What's your approach?",
                            "options": [
                                "A. I thank them and reflect on it later.",
                                "B. I argue my point.",
                                "C. I dismiss it entirely.",
                                "D. I feel offended and withdraw."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How often do you consider others' feelings before speaking?",
                            "options": [
                                "A. Always.",
                                "B. Most of the time.",
                                "C. Occasionally.",
                                "D. Rarely."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "When you're excited or happy, how do you react?",
                            "options": [
                                "A. I share it openly with others.",
                                "B. I smile but keep it to myself.",
                                "C. I feel it internally but don't show it.",
                                "D. I feel uncomfortable expressing happiness."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How often do you reflect on your emotional state?",
                            "options": [
                                "A. Daily or regularly.",
                                "B. Occasionally.",
                                "C. Only when something's wrong.",
                                "D. I rarely think about it."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "What do you do when someone shares their emotional struggles?",
                            "options": [
                                "A. Listen actively and validate them.",
                                "B. Try to solve their problem immediately.",
                                "C. Change the topic.",
                                "D. Feel awkward and quiet."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do you act when someone disagrees with your opinion?",
                            "options": [
                                "A. I try to understand their point of view.",
                                "B. I defend my opinion strongly.",
                                "C. I get annoyed or take it personally.",
                                "D. I avoid further discussion."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do you motivate yourself when you're feeling low?",
                            "options": [
                                "A. I set small goals to lift my mood.",
                                "B. I talk to a friend or mentor.",
                                "C. I wait and hope I feel better.",
                                "D. I often struggle to motivate myself."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How aware are you of the emotional atmosphere in a room?",
                            "options": [
                                "A. Very aware – I pick up on it quickly.",
                                "B. Somewhat aware.",
                                "C. I notice if it's extreme.",
                                "D. I'm usually focused on my own state."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "Do you find it easy to build emotional connections with others?",
                            "options": [
                                "A. Yes, I connect deeply with people.",
                                "B. Only with close friends.",
                                "C. I struggle to form deep bonds.",
                                "D. I prefer to keep emotions out of relationships."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do you manage emotional conflict at work?",
                            "options": [
                                "A. Address it calmly and directly.",
                                "B. Avoid it whenever possible.",
                                "C. Let someone else handle it.",
                                "D. Suppress my emotions until it passes."
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do you respond to positive feedback?",
                            "options": [
                                "A. I accept it with appreciation.",
                                "B. I feel awkward but grateful.",
                                "C. I downplay it.",
                                "D. I don't believe it's genuine."
                            ]
                        }
                    ]
        elif test.title == "Gen Z vs Millennial vs Alpha Test":
            fallback_questions = [
                        {
                            "id": str(uuid.uuid4()),
                            "question": "Which form of communication do you prefer most?",
                            "options": [
                                "A. Text messaging",
                                "B. Voice notes",
                                "C. Email",
                                "D. FaceTime or video calls"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "What's your favorite way to consume media?",
                            "options": [
                                "A. YouTube",
                                "B. Netflix or OTT platforms",
                                "C. TikTok or Instagram Reels",
                                "D. TV or traditional media"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "Which of these devices do you use the most?",
                            "options": [
                                "A. Smartphone",
                                "B. Tablet/iPad",
                                "C. Laptop",
                                "D. Smartwatch or voice assistant"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do you prefer to learn something new?",
                            "options": [
                                "A. Watching short videos",
                                "B. Reading step-by-step articles",
                                "C. Through interactive apps or games",
                                "D. Classroom-style instruction"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "What would you likely do when facing a tech issue?",
                            "options": [
                                "A. Google it or check Reddit",
                                "B. Watch a tutorial on YouTube",
                                "C. Ask a friend or family member",
                                "D. Try random things until it works"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "What is your opinion on working from home?",
                            "options": [
                                "A. It's the future — flexibility is key",
                                "B. Hybrid work is ideal",
                                "C. Prefer office for social interaction",
                                "D. I'm still in school"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "Which social platform do you use the most?",
                            "options": [
                                "A. Instagram",
                                "B. TikTok",
                                "C. Facebook",
                                "D. Snapchat"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "Which type of content appeals to you the most?",
                            "options": [
                                "A. Memes and relatable videos",
                                "B. Life hacks and productivity tips",
                                "C. Long-form storytelling",
                                "D. Animated or gamified content"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "Which describes your view of career success?",
                            "options": [
                                "A. Freedom and passion matter most",
                                "B. Climbing the corporate ladder",
                                "C. Having a personal brand",
                                "D. I haven't thought about it yet"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do you usually shop?",
                            "options": [
                                "A. Through apps with reviews",
                                "B. Online with influencer suggestions",
                                "C. Traditional retail stores",
                                "D. Voice search or smart devices"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "Which phrase sounds most like you?",
                            "options": [
                                "A. 'No cap, that's fire!'",
                                "B. 'Adulting is hard.'",
                                "C. 'YOLO!'",
                                "D. 'Alexa, play my playlist.'"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do you usually express your opinion online?",
                            "options": [
                                "A. Create a short video or meme",
                                "B. Share a story or reel",
                                "C. Write a blog or comment post",
                                "D. I don't share online opinions"
                            ]
                        }
                    ]

        elif test.title == "Myers-Briggs Type Indicator":
            fallback_questions =[
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do you prefer to recharge after a long day?",
                            "options": [
                                "A. Spend time with friends or family",
                                "B. Go out and do something fun",
                                "C. Read a book or listen to music alone",
                                "D. Take time alone to reflect and rest"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "Which best describes how you make decisions?",
                            "options": [
                                "A. Based on facts and logic",
                                "B. With consideration of people's feelings",
                                "C. I evaluate both feelings and facts equally",
                                "D. I go with my gut feeling"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do you typically plan your day?",
                            "options": [
                                "A. With a clear list and schedule",
                                "B. I like to have some structure, but stay flexible",
                                "C. I go with the flow and decide as the day progresses",
                                "D. I prefer spontaneity and avoid rigid plans"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "When learning something new, you prefer:",
                            "options": [
                                "A. Step-by-step instructions with examples",
                                "B. Learning through hands-on experience",
                                "C. Abstract ideas and concepts",
                                "D. Exploring possibilities and connections"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do you feel about attending large social events?",
                            "options": [
                                "A. I love them and feel energized",
                                "B. I enjoy them occasionally",
                                "C. I attend, but they drain me",
                                "D. I prefer smaller, intimate gatherings"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "What influences your decisions the most?",
                            "options": [
                                "A. Objective analysis",
                                "B. Empathy and values",
                                "C. Efficiency and outcome",
                                "D. Harmony and relationships"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do you respond to unexpected changes in plans?",
                            "options": [
                                "A. I adapt quickly without stress",
                                "B. I try to go along but prefer to stick to the plan",
                                "C. I get anxious and need time to adjust",
                                "D. I enjoy the flexibility and see it as an adventure"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "In a group project, what role do you usually take?",
                            "options": [
                                "A. The leader or organizer",
                                "B. The creative idea generator",
                                "C. The thoughtful planner",
                                "D. The supporter who ensures team harmony"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "Which best describes your focus?",
                            "options": [
                                "A. The here and now",
                                "B. Practical details",
                                "C. Future possibilities",
                                "D. Big-picture thinking"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "Which statement resonates more?",
                            "options": [
                                "A. I prefer making decisions quickly",
                                "B. I prefer keeping options open",
                                "C. I like things settled and predictable",
                                "D. I like to explore until the last moment"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do you approach conflict?",
                            "options": [
                                "A. Direct and logical",
                                "B. Seek peace and understanding",
                                "C. Avoid it whenever possible",
                                "D. Address it with empathy and diplomacy"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "What motivates you more?",
                            "options": [
                                "A. Personal growth and self-reflection",
                                "B. Achieving goals efficiently",
                                "C. Being helpful to others",
                                "D. Exploring new ideas and creativity"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do you prepare for a trip?",
                            "options": [
                                "A. I plan everything in advance",
                                "B. I pack early and prepare a list",
                                "C. I pack last minute but mentally plan",
                                "D. I go with whatever feels right at the time"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "What's your preferred work environment?",
                            "options": [
                                "A. Structured and routine-based",
                                "B. Dynamic and fast-paced",
                                "C. Collaborative and friendly",
                                "D. Independent and flexible"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "When making decisions, do you:",
                            "options": [
                                "A. Trust logic over feelings",
                                "B. Balance heart and head",
                                "C. Let emotions guide you",
                                "D. Follow what seems ethically right"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do you process information?",
                            "options": [
                                "A. Through experience and facts",
                                "B. By spotting trends and meanings",
                                "C. By verifying details thoroughly",
                                "D. By imagining possibilities and alternatives"
                            ]
                        }
                    ]

        elif test.title == "Risk Tolerance Assessment":
            fallback_questions = [
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do you feel about making big decisions with incomplete information?",
                            "options": [
                                "A. I avoid making a decision until I have all the facts",
                                "B. I make a cautious choice and minimize risks",
                                "C. I weigh pros and cons and act if odds seem favorable",
                                "D. I trust my gut and go for it"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "What would you do if you had the chance to invest in a new but unproven startup?",
                            "options": [
                                "A. Avoid it entirely",
                                "B. Consider it only after extensive research",
                                "C. Invest a small amount to test the waters",
                                "D. Jump at the opportunity"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "When traveling, you prefer:",
                            "options": [
                                "A. Planned tours and itineraries",
                                "B. Pre-booked schedules with room for change",
                                "C. Minimal planning and go with the flow",
                                "D. Spontaneous adventures without a plan"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do you feel about quitting a stable job for a promising startup?",
                            "options": [
                                "A. Never – I value stability too much",
                                "B. Only if I have financial backup",
                                "C. If the startup has strong backing and vision",
                                "D. I'm always open to new challenges"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "In a financial downturn, what would be your reaction?",
                            "options": [
                                "A. Pull out all investments to prevent loss",
                                "B. Rebalance and move to safer options",
                                "C. Wait patiently for the market to recover",
                                "D. Buy more while prices are low"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "What kind of career path excites you more?",
                            "options": [
                                "A. Secure job with consistent pay",
                                "B. Corporate ladder with benefits",
                                "C. Freelancing with moderate uncertainty",
                                "D. Entrepreneurship with unlimited upside"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "You're offered a chance to skydive. Your response?",
                            "options": [
                                "A. Absolutely not",
                                "B. Maybe, if others are doing it",
                                "C. I'll try once with a professional",
                                "D. Let's go!"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do you handle sudden changes in plans?",
                            "options": [
                                "A. I get frustrated and need time to adjust",
                                "B. I try to adapt but prefer consistency",
                                "C. I'm okay with minor changes",
                                "D. I thrive in unexpected situations"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "What's your investment style?",
                            "options": [
                                "A. Fixed deposits and savings accounts",
                                "B. Balanced mutual funds",
                                "C. Stocks and ETFs",
                                "D. Crypto and early-stage startups"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How would you feel about moving to a new city with no job yet lined up?",
                            "options": [
                                "A. Not a chance",
                                "B. Only with some savings and a fallback plan",
                                "C. I'll try it if the opportunity feels right",
                                "D. I'd love the thrill of it"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "In group decisions, you're most likely to:",
                            "options": [
                                "A. Follow the most cautious plan",
                                "B. Support the consensus",
                                "C. Suggest a bold idea with justification",
                                "D. Push for high-risk, high-reward moves"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "If given an unknown dish at a restaurant, you'd:",
                            "options": [
                                "A. Stick to what I know",
                                "B. Ask about it, then maybe try it",
                                "C. Taste it out of curiosity",
                                "D. Order it without hesitation"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "You receive an unexpected opportunity with both great reward and great risk. You:",
                            "options": [
                                "A. Decline – not worth the risk",
                                "B. Consider it but set strict limits",
                                "C. Analyze and take a calculated leap",
                                "D. Embrace it quickly – rewards matter most"
                            ]
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "question": "How do you feel when someone calls you a risk-taker?",
                            "options": [
                                "A. Uncomfortable – I prefer safety",
                                "B. Unsure – I don't see myself that way",
                                "C. Neutral – sometimes I am, sometimes I'm not",
                                "D. Proud – I like taking risks"
                            ]
                        }
                    ]

        else:
            fallback_questions = []
        return fallback_questions

def generate_test_result(test, answers):
    """Generate test result using GPT-4o-mini based on user's answers"""
    import openai
    import json
    from django.conf import settings
    
    # Set up OpenAI API
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    
    # Prepare the answers for the prompt
    answers_text = ""
    for q_id, answer_data in answers.items():
        question = answer_data['question']
        answer = answer_data['answer']
        options = answer_data['options']
        answer_text = options[int(answer)] if answer.isdigit() and int(answer) < len(options) else answer
        answers_text += f"Question: {question}\nAnswer: {answer_text}\n\n"
    
    # Prepare prompt
    prompt = f"""Based on the following answers to a {test.title} test, generate a comprehensive personality profile:

{answers_text}

Return a JSON object with the following structure:
{{
    "title": "A concise, catchy title for the result (max 50 characters)",
    "description": "A detailed 3-4 paragraph analysis of the personality profile, including insights and general observations",
    "traits": {{
        "openness": 75,
        "conscientiousness": 60,
        "extraversion": 45,
        "agreeableness": 80,
        "neuroticism": 30
    }},
    "strengths": [
        "Strength 1",
        "Strength 2",
        "Strength 3",
        "Strength 4"
    ],
    "weaknesses": [
        "Area for growth 1",
        "Area for growth 2",
        "Area for growth 3",
        "Area for growth 4"
    ],
    "recommendations": [
        {{
            "title": "Recommendation 1",
            "description": "Brief explanation of this recommendation"
        }},
        {{
            "title": "Recommendation 2",
            "description": "Brief explanation of this recommendation"
        }},
        {{
            "title": "Recommendation 3",
            "description": "Brief explanation of this recommendation"
        }}
    ],
    "compatibility": 78,
    "accuracy": "High"
}}

Note that traits should be percentages between 0-100, compatibility should be a percentage between 0-100, and accuracy should be "Low", "Medium", or "High".
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a personality assessment expert who provides insightful and accurate personality profiles."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        )
        
        # Extract and parse the JSON response
        content = response.choices[0].message.content
        # Find JSON content between ```json and ``` if present
        import re
        json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
            
        result_data = json.loads(content)
        
        # Store the full result data in the description field
        # The template will extract and display the different components
        full_result = {
            "title": result_data["title"],
            "description": result_data["description"],
            "traits": result_data.get("traits", {
                "openness": 75,
                "conscientiousness": 60,
                "extraversion": 45,
                "agreeableness": 80,
                "neuroticism": 30
            }),
            "strengths": result_data.get("strengths", [
                "Creative thinking and problem-solving",
                "Strong attention to detail",
                "Excellent at building relationships",
                "Adaptable to changing situations"
            ]),
            "weaknesses": result_data.get("weaknesses", [
                "May struggle with public speaking",
                "Could benefit from more assertiveness",
                "Sometimes overthinks decisions",
                "May avoid necessary confrontation"
            ]),
            "recommendations": result_data.get("recommendations", [
                {"title": "Practice Mindfulness", "description": "Daily mindfulness exercises can help you manage stress and improve your decision-making process."},
                {"title": "Seek New Experiences", "description": "Your personality thrives when exposed to novel situations. Try to incorporate new activities into your routine."},
                {"title": "Build Support Networks", "description": "Connect with like-minded individuals who can provide insights and support for your personal growth."}
            ]),
            "compatibility": result_data.get("compatibility", 78),
            "accuracy": result_data.get("accuracy", "High")
        }
        
        # Convert the full result to a JSON string to store in the description field
        full_result_json = json.dumps(full_result)
        
        return result_data["title"], full_result_json
        
    except Exception as e:
        # Fallback to generic result if API fails
        print(f"Error generating result: {str(e)}")
        fallback_result = {
            "title": f"{test.title} Result",
            "description": f"Based on your answers, you show interesting patterns in how you approach {test.title.lower()} scenarios. Your responses indicate a balanced perspective with some unique insights. Continue exploring these aspects of yourself to gain deeper understanding.",
            "traits": {
                "openness": 75,
                "conscientiousness": 60,
                "extraversion": 45,
                "agreeableness": 80,
                "neuroticism": 30
            },
            "strengths": [
                "Creative thinking and problem-solving",
                "Strong attention to detail",
                "Excellent at building relationships",
                "Adaptable to changing situations"
            ],
            "weaknesses": [
                "May struggle with public speaking",
                "Could benefit from more assertiveness",
                "Sometimes overthinks decisions",
                "May avoid necessary confrontation"
            ],
            "recommendations": [
                {"title": "Practice Mindfulness", "description": "Daily mindfulness exercises can help you manage stress and improve your decision-making process."},
                {"title": "Seek New Experiences", "description": "Your personality thrives when exposed to novel situations. Try to incorporate new activities into your routine."},
                {"title": "Build Support Networks", "description": "Connect with like-minded individuals who can provide insights and support for your personal growth."}
            ],
            "compatibility": 78,
            "accuracy": "High"
        }
        return fallback_result["title"], json.dumps(fallback_result)

@login_required
def upgrade_subscription_view(request):
    """View for selecting a subscription plan"""
    return render(request, 'core/upgrade_subscription.html')

@login_required
def payment_view(request):
    """View for processing payments"""
    plan = request.GET.get('plan', 'monthly')
    
    # Base prices in INR
    if plan == 'monthly':
        plan_name = "Monthly Premium"
        base_price = 999.00  # Base price in INR
        gst_rate = 0.18  # 18% GST
        gst_amount = round(base_price * gst_rate, 2)
        total_price = base_price + gst_amount
        amount_in_paise = int(total_price * 100)  # Convert to paise (smallest currency unit in INR)
        duration_days = 30
    else:  # annual
        plan_name = "Annual Premium"
        base_price = 9999.00  # Base price in INR
        gst_rate = 0.18  # 18% GST
        gst_amount = round(base_price * gst_rate, 2)
        total_price = base_price + gst_amount
        amount_in_paise = int(total_price * 100)  # Convert to paise
        duration_days = 365
    
    if request.method == 'POST':
        payment_id = request.POST.get('razorpay_payment_id')
        razorpay_order_id = request.POST.get('razorpay_order_id')
        signature = request.POST.get('razorpay_signature')
        
        print(f"[DEBUG] Payment POST received: payment_id={payment_id}, order_id={razorpay_order_id}")
        
        if not payment_id:
            messages.error(request, "Payment processing failed. Please try again.")
            print(f"[ERROR] Missing payment_id in request")
            return redirect('core:payment_failed')
        
        try:
            # Verify the payment signature
            params_dict = {
                'razorpay_payment_id': payment_id,
                'razorpay_order_id': razorpay_order_id,
                'razorpay_signature': signature
            }
            
            print(f"[DEBUG] Verifying payment signature for order {razorpay_order_id}")
            # Verify the payment signature
            razorpay_client.utility.verify_payment_signature(params_dict)
            print(f"[DEBUG] Payment signature verification successful")
            
            # For demo purposes, we'll simulate a successful payment
            profile = request.user.profile
            before_premium = profile.is_premium
            before_expires = profile.premium_expires
            
            print(f"[DEBUG] Before activation - User: {request.user.username}, Premium: {before_premium}, Expires: {before_expires}")
            
            profile.payment_method_id = payment_id  # Store payment ID
            profile.activate_subscription(plan, duration_days)
            
            # Verify the subscription was activated
            profile.refresh_from_db()
            after_premium = profile.is_premium
            after_expires = profile.premium_expires
            
            print(f"[DEBUG] After activation - User: {request.user.username}, Premium: {after_premium}, Expires: {after_expires}")
            
            # Track this payment in user activity logs
            from core.models import UserActivity
            UserActivity.log_activity(request.user, 'payment_successful', None)
            
            # Prepare success page data
            next_billing_date = timezone.now() + timedelta(days=duration_days)
            
            return render(request, 'core/payment_success.html', {
                'plan_name': plan_name,
                'plan_price': f"₹{total_price:,.2f}",
                'next_billing_date': next_billing_date.strftime('%B %d, %Y'),
                'payment_id': payment_id[:4] + "..."  # Show partial payment ID
            })
            
        except Exception as e:
            print(f"[ERROR] Payment verification failed: {str(e)}")
            messages.error(request, f"Payment verification failed: {str(e)}")
            return render(request, 'core/payment_failed.html', {
                'error_message': str(e),
                'plan': plan
            })
    
    # For GET requests, create a new Razorpay order
    try:
        # Create a Razorpay Order
        razorpay_order = razorpay_client.order.create({
            'amount': amount_in_paise,
            'currency': 'INR',
            'payment_capture': '1',  # Auto capture
            'notes': {
                'plan': plan,
                'user_id': str(request.user.id)
            }
        })
        
        print(f"[DEBUG] Created Razorpay order: {razorpay_order['id']} for user {request.user.username}")
        
        # Prepare context for the payment page
        context = {
            'plan': plan,
            'plan_name': plan_name,
            'base_price': f"₹{base_price:,.2f}",
            'gst_amount': f"₹{gst_amount:,.2f}",
            'total_price': f"₹{total_price:,.2f}",
            'gst_percentage': int(gst_rate * 100),
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'razorpay_order_id': razorpay_order['id'],
            'callback_url': request.build_absolute_uri(reverse('core:payment')),
            'user_name': request.user.get_full_name() or request.user.username,
            'user_email': request.user.email,
            'amount': amount_in_paise,
        }
        
        return render(request, 'core/payment.html', context)
        
    except Exception as e:
        print(f"[ERROR] Error creating payment order: {str(e)}")
        messages.error(request, f"Error creating payment order: {str(e)}")
        return redirect('core:upgrade_subscription')

@login_required
def payment_success_view(request):
    """View for successful payments"""
    return render(request, 'core/payment_success.html')

@login_required
def payment_failed_view(request):
    """View for failed payments"""
    return render(request, 'core/payment_failed.html')

@login_required
def cancel_subscription_view(request):
    """View for canceling subscriptions"""
    if request.method == 'POST':
        # In a real implementation, you would cancel the subscription in Stripe
        profile = request.user.profile
        profile.cancel_subscription()
        messages.success(request, "Your subscription has been canceled. You will have access until the end of your billing period.")
        return redirect('core:setting')
    
    # Show confirmation page for GET requests
    return render(request, 'core/cancel_subscription.html')

# Chat room functionality has been removed

# Chat room functionality has been removed

# Chat room functionality has been removed

# Chat room functionality has been removed

@login_required
def search_users(request):
    """
    Search for users by name or email
    Used by the chat interface
    """
    query = request.GET.get('q', '')
    users = User.objects.filter(
    (Q(username__icontains=query) | Q(email__icontains=query)) & 
    ~Q(id=request.user.id)
    )[:10]
    
    return render(request, 'core/partials/user_search_results.html', {'users': users})

@login_required
def api_search_users(request):
    """
    API endpoint for searching users by name or email
    Returns JSON response with user data
    """
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'users': []})
    
    users = User.objects.filter(
        (Q(username__icontains=query) | Q(email__icontains=query)) & 
        ~Q(id=request.user.id)
    )[:10]
    
    user_data = [
        {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': f"{user.first_name} {user.last_name}".strip()
        }
        for user in users
    ]
    
    return JsonResponse({'users': user_data})

@login_required
@require_POST
def api_share_scenario_result(request):
    """
    API endpoint for sharing scenario results with other users
    Expects JSON with:
    - scenario_id: ID of the scenario
    - user_ids: List of user IDs to share with
    - scenario_title: Title of the scenario
    - score: Total score for the scenario
    
    Returns JSON response with status
    """
    try:
        data = json.loads(request.body)
        scenario_id = data.get('scenario_id')
        user_ids = data.get('user_ids', [])
        scenario_title = data.get('scenario_title', '')
        score = data.get('score', 0)
        
        if not scenario_id or not user_ids:
            return JsonResponse({'status': 'error', 'message': 'Missing required parameters'}, status=400)
        
        # Get the scenario
        scenario = get_object_or_404(Scenario, id=scenario_id)
        
        # Share with each user
        for user_id in user_ids:
            try:
                recipient = User.objects.get(id=user_id)
                
                # Create a direct message
                message = DirectMessage.objects.create(
                    sender=request.user,
                    recipient=recipient,
                    message=f"I'm sharing my result for '{scenario_title}'. I scored {score} points!",
                    message_type='scenario',
                    data={
                        'scenario_id': scenario_id,
                        'title': scenario_title,
                        'score': score
                    }
                )
                
                # Create or update conversation
                conversation, created = Conversation.objects.get_or_create(
                    initiator=request.user, 
                    receiver=recipient,
                    defaults={
                        'last_message': message.message,
                        'last_message_time': message.created_at,
                        'unread_count': 1
                    }
                )
                
                if not created:
                    conversation.last_message = message.message
                    conversation.last_message_time = message.created_at
                    conversation.unread_count += 1
                    conversation.save()
                    
                # Check for reverse conversation
                reverse_conversation, _ = Conversation.objects.get_or_create(
                    initiator=recipient, 
                    receiver=request.user,
                    defaults={
                        'last_message': message.message,
                        'last_message_time': message.created_at,
                        'unread_count': 0
                    }
                )
                
                if not _:
                    reverse_conversation.last_message = message.message
                    reverse_conversation.last_message_time = message.created_at
                    reverse_conversation.save()
                
            except User.DoesNotExist:
                continue
        
        return JsonResponse({'status': 'success', 'message': 'Scenario result shared successfully'})
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@require_POST
def api_share_test_result(request):
    """
    API endpoint for sharing personality test results with other users
    Expects JSON with:
    - result_id: ID of the test result
    - test_id: ID of the test
    - user_ids: List of user IDs to share with
    - result_title: Title of the result
    - test_title: Title of the test
    
    Returns JSON response with status
    """
    try:
        data = json.loads(request.body)
        result_id = data.get('result_id')
        test_id = data.get('test_id')
        user_ids = data.get('user_ids', [])
        result_title = data.get('result_title', '')
        test_title = data.get('test_title', '')
        
        if not result_id or not test_id or not user_ids:
            return JsonResponse({'status': 'error', 'message': 'Missing required parameters'}, status=400)
        
        # Get the test result
        test_result = get_object_or_404(PersonalityTestResult, id=result_id, user=request.user)
        
        # Share with each user
        for user_id in user_ids:
            try:
                recipient = User.objects.get(id=user_id)
                
                # Create a direct message
                message = DirectMessage.objects.create(
                    sender=request.user,
                    recipient=recipient,
                    message=f"I'm sharing my result '{result_title}' from the {test_title} test!",
                    message_type='test_result',
                    data={
                        'result_id': result_id,
                        'test_id': test_id,
                        'result_title': result_title,
                        'test_title': test_title
                    }
                )
                
                # Create or update conversation
                conversation, created = Conversation.objects.get_or_create(
                    initiator=request.user, 
                    receiver=recipient,
                    defaults={
                        'last_message': message.message,
                        'last_message_time': message.created_at,
                        'unread_count': 1
                    }
                )
                
                if not created:
                    conversation.last_message = message.message
                    conversation.last_message_time = message.created_at
                    conversation.unread_count += 1
                    conversation.save()
                    
                # Check for reverse conversation
                reverse_conversation, _ = Conversation.objects.get_or_create(
                    initiator=recipient, 
                    receiver=request.user,
                    defaults={
                        'last_message': message.message,
                        'last_message_time': message.created_at,
                        'unread_count': 0
                    }
                )
                
                if not _:
                    reverse_conversation.last_message = message.message
                    reverse_conversation.last_message_time = message.created_at
                    reverse_conversation.save()
                
            except User.DoesNotExist:
                continue
        
        return JsonResponse({'status': 'success', 'message': 'Test result shared successfully'})
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@log_request_performance
def sse_chat_messages(request, user_id):
    """Server-Sent Events endpoint for receiving chat messages"""
    other_user = get_object_or_404(User, id=user_id)
    current_user = request.user
    
    # Create a unique conversation ID (sorted user IDs to ensure consistency)
    user_ids = sorted([str(current_user.id), str(other_user.id)])
    conversation_id = f"chat_{user_ids[0]}_{user_ids[1]}"
    
    # Initialize queue for this conversation if it doesn't exist
    if conversation_id not in message_queues:
        message_queues[conversation_id] = []
        
    # Use a max size for message queues to prevent memory leaks
    MAX_QUEUE_SIZE = 100
    if len(message_queues[conversation_id]) > MAX_QUEUE_SIZE:
        # Remove older messages if queue is too large
        message_queues[conversation_id] = message_queues[conversation_id][-MAX_QUEUE_SIZE:]
    
    # Get last_id from query parameters - this is to help with missed messages
    try:
        last_message_count = int(request.GET.get('last_id', 0))
        # Limit how many messages we fetch to prevent timeouts
        last_message_count = min(last_message_count, 30)
    except ValueError:
        last_message_count = 0
    
    # Add recent messages from DB if the queue is empty but we have messages in the DB
    if len(message_queues[conversation_id]) == 0:
        # Get recent messages from DB with efficient query
        recent_messages = (DirectMessage.get_conversation(current_user, other_user)
                           .select_related('sender', 'shared_scenario')
                           .order_by('-timestamp')[:20])
        
        # Add to queue in reverse order (oldest first)
        for message in reversed(list(recent_messages)):
            # Skip if we already have enough messages based on last_id
            if len(message_queues[conversation_id]) >= last_message_count:
                break
                
            message_data = {
                'type': 'scenario' if message.shared_scenario else 'text',
                'message': message.content,
                'username': message.sender.username,
                'user_id': message.sender.id,
                'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            if message.shared_scenario:
                message_data['scenario'] = {
                    'id': message.shared_scenario.id,
                    'title': message.shared_scenario.title,
                    'description': message.shared_scenario.description,
                    'category': message.shared_scenario.category,
                    'difficulty': message.shared_scenario.difficulty
                }
                
            # Add to the front of the queue
            message_queues[conversation_id].insert(0, message_data)
    
    def event_stream():
        # Send initial connection established event
        yield f"data: {json.dumps({'type': 'connection', 'message': 'Connection established'})} \n\n"
        
        # Keep track of the last message index we processed
        # Start with what the client already knows
        last_message_index = min(last_message_count, len(message_queues[conversation_id]))
        
        # Keep connection open and check for new messages
        last_check = time.time()
        
        while True:
            # Check for new messages in the queue
            current_queue_length = len(message_queues[conversation_id])
            if current_queue_length > last_message_index:
                # Send all new messages
                for i in range(last_message_index, current_queue_length):
                    message_data = message_queues[conversation_id][i]
                    yield f"data: {json.dumps(message_data)} \n\n"
                
                # Update the last message index
                last_message_index = current_queue_length
            
            # Heartbeat every 30 seconds to keep connection alive
            if time.time() - last_check > 30:
                yield f"data: {json.dumps({'type': 'heartbeat'})} \n\n"
                last_check = time.time()
            
            time.sleep(0.5)  # Check twice per second for better responsiveness
    
    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Disable buffering for Nginx
    return response

@login_required
@csrf_exempt
def send_chat_message(request, user_id):
    """API endpoint for sending chat messages"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    other_user = get_object_or_404(User, id=user_id)
    current_user = request.user
    
    try:
        data = json.loads(request.body)
        message_content = data.get('message', '').strip()
        message_type = data.get('type', 'text')
        scenario_id = data.get('scenario_id')
        
        if not message_content:
            return JsonResponse({'error': 'Message cannot be empty'}, status=400)
        
        # Create a unique conversation ID
        user_ids = sorted([str(current_user.id), str(other_user.id)])
        conversation_id = f"chat_{user_ids[0]}_{user_ids[1]}"
        
        # Initialize queue for this conversation if it doesn't exist
        if conversation_id not in message_queues:
            message_queues[conversation_id] = []
        
        # Create and save the message
        if message_type == 'share_scenario' and scenario_id:
            # Handle scenario sharing
            try:
                scenario = Scenario.objects.get(id=scenario_id)
                message = DirectMessage.objects.create(
                    sender=current_user,
                    recipient=other_user,
                    content=message_content,
                    shared_scenario=scenario
                )
                
                # Prepare scenario data for the event
                scenario_data = {
                    'id': scenario.id,
                    'title': scenario.title,
                    'description': scenario.description,
                    'category': scenario.category,
                    'difficulty': scenario.difficulty
                }
                
                # Add message to the queue
                message_queues[conversation_id].append({
                    'type': 'scenario',
                    'message': message_content,
                    'username': current_user.username,
                    'user_id': current_user.id,
                    'scenario': scenario_data,
                    'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                })
                
            except Scenario.DoesNotExist:
                return JsonResponse({'error': 'Scenario not found'}, status=404)
        else:
            # Handle regular text message
            message = DirectMessage.objects.create(
                sender=current_user,
                recipient=other_user,
                content=message_content
            )
            
            # Add message to the queue
            message_queues[conversation_id].append({
                'type': 'text',
                'message': message_content,
                'username': current_user.username,
                'user_id': current_user.id,
                'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return JsonResponse({'status': 'success'})
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def create_issue_view(request):
    if request.method == 'POST':
        form = IssueForm(request.POST)
        if form.is_valid():
            issue = form.save(commit=False)
            issue.user = request.user
            issue.save()
            messages.success(request, "Your issue has been submitted successfully.")
            return redirect('core:issue_detail', issue_id=issue.id)
    else:
        form = IssueForm()
    
    return render(request, 'core/create_issue.html', {'form': form})

@login_required
def issue_detail_view(request, issue_id):
    issue = get_object_or_404(SupportIssue, id=issue_id)
    
    # Check if the user is the owner of the issue or a staff member
    if issue.user != request.user and not request.user.is_staff:
        messages.error(request, "You don't have permission to view this issue.")
        return redirect('core:support')
    
    # Get all comments for this issue
    comments = issue.comments.all()
    
    # Handle comment submission
    if request.method == 'POST':
        comment_form = IssueCommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.issue = issue
            comment.user = request.user
            comment.is_staff_comment = request.user.is_staff
            comment.save()
            
            # Update the issue's updated_at timestamp
            issue.save()  # This will update the auto_now field
            
            messages.success(request, "Your comment has been added.")
            return redirect('core:issue_detail', issue_id=issue.id)
    else:
        comment_form = IssueCommentForm()
    
    context = {
        'issue': issue,
        'comments': comments,
        'comment_form': comment_form
    }
    
    return render(request, 'core/issue_detail.html', context)

@login_required
def all_issues_view(request):
    # Get all issues for the current user
    user_issues = SupportIssue.objects.filter(user=request.user)
    
    context = {
        'issues': user_issues
    }
    
    return render(request, 'core/all_issues.html', context)

# Chat room functionality has been removed

# Chat room functionality has been removed

# Chat room functionality has been removed

# Chat room functionality has been removed

@login_required
def create_personal_chat(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        
        try:
            other_user = User.objects.get(id=user_id)
            messages.success(request, f"Started a chat with {other_user.username}")
            return redirect('core:direct_message', user_id=other_user.id)
            
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect('core:create_personal_chat')
    
    # Handle GET request parameter for user_id
    user_id = request.GET.get('user_id')
    if user_id:
        try:
            other_user = User.objects.get(id=user_id)
            return redirect('core:direct_message', user_id=other_user.id)
        except User.DoesNotExist:
            messages.error(request, "User not found.")
    
    # Get users to chat with (excluding self)
    users = User.objects.exclude(id=request.user.id)
    
    return render(request, 'core/create_personal_chat.html', {'users': users})

@login_required
def top_members_view(request):
    # Get top members based on activity score
    top_members = User.objects.annotate(
        level=F('profile__level'),
        xp=F('profile__xp_points'),
        streak=F('profile__daily_streak'),
        scenarios=F('profile__total_scenarios_completed'),
        activity_score=F('profile__xp_points') + (F('profile__daily_streak') * 10) + 
                      (F('profile__total_scenarios_completed') * 5) + 
                      (F('profile__total_comments') * 2) + 
                      (F('profile__total_likes_received') * 1) + 
                      (F('profile__total_posts') * 3)
    ).order_by('-activity_score')
    
    # Assign ranks
    for i, user in enumerate(top_members, 1):
        user.rank = i
    
    context = {
        'top_members': top_members
    }
    
    return render(request, 'core/top_members.html', context)

@login_required
def user_profile_view(request, user_id):
    profile_user = get_object_or_404(User, id=user_id)
    profile = profile_user.profile
    
    # Get user's recent activities
    recent_activities = UserActivity.objects.filter(user=profile_user).order_by('-created_at')[:10]
    
    # Get user's stats
    user_stats = {
        'rank': profile.rank,
        'level': profile.level,
        'xp': profile.xp_points,
        'streak': profile.daily_streak,
        'scenarios_completed': profile.total_scenarios_completed,
        'comments': profile.total_comments,
        'likes_received': profile.total_likes_received,
        'posts': profile.total_posts,
        'activity_score': profile.activity_score
    }
    
    context = {
        'profile_user': profile_user,
        'profile': profile,
        'user_stats': user_stats,
        'recent_activities': recent_activities
    }
    
    return render(request, 'core/user_profile.html', context)

@login_required
def recent_activities_view(request):
    # Get all recent activities
    activities = UserActivity.objects.all().order_by('-created_at')[:50]
    
    context = {
        'activities': activities
    }
    
    return render(request, 'core/recent_activities.html', context)

@login_required
@log_request_performance
def get_community_messages(request):
    """API endpoint to get community messages via AJAX"""
    last_id = request.GET.get('last_id', 0)
    limit = request.GET.get('limit', 20)  # Default to 20 messages per request
    
    try:
        last_id = int(last_id)
        limit = min(int(limit), 50)  # Cap at 50 to prevent excessive queries
    except ValueError:
        last_id = 0
        limit = 20
    
    # Get community messages after the last_id with optimized query
    messages = CommunityMessage.objects.select_related('sender')
    
    if last_id > 0:
        messages = messages.filter(id__gt=last_id)
    
    # Add ordering and limit to reduce memory usage
    messages = messages.order_by('id')[:limit]
    
    # Format messages for JSON response - avoid duplicate processing
    messages_data = []
    current_user_id = request.user.id
    
    for msg in messages:
        messages_data.append({
            'id': msg.id,
            'content': msg.content,
            'sender': msg.sender.username,
            'user_id': msg.sender.id,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'is_own': msg.sender.id == current_user_id
        })
    
    return JsonResponse({'messages': messages_data})

@login_required
@csrf_exempt
@require_POST
def send_community_message(request):
    """API endpoint to send community messages via AJAX"""
    try:
        data = json.loads(request.body)
        content = data.get('message', '').strip()
        
        if not content:
            return JsonResponse({'status': 'error', 'error': 'Message cannot be empty'}, status=400)
        
        # Create the message
        message = CommunityMessage.objects.create(
            sender=request.user,
            content=content
        )
        
        # Log activity
        UserActivity.log_activity(request.user, 'message', None)
        
        return JsonResponse({
            'status': 'success',
            'message': {
                'id': message.id,
                'content': message.content,
                'sender': request.user.username,
                'user_id': request.user.id,
                'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'is_own': True
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)

@login_required
def send_community_message_form(request):
    """Handle form submission for sending community messages"""
    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
        
        if message:
            # Create the message
            CommunityMessage.objects.create(
                sender=request.user,
                content=message
            )
            
            # Log activity
            UserActivity.log_activity(request.user, 'message', None)
    
    # Redirect back to community page
    return redirect('core:community')

# Error handlers
def handler404(request, exception):
    """Custom 404 page not found handler"""
    return render(request, 'core/404.html', status=404)

def handler500(request):
    """Custom 500 server error handler"""
    return render(request, 'core/500.html', status=500)

def handler403(request, exception):
    """Custom 403 permission denied handler"""
    return render(request, 'core/403.html', status=403)

def handler400(request, exception):
    """Custom 400 bad request handler"""
    return render(request, 'core/400.html', status=400)

def handler408(request, exception=None):
    """Custom 408 request timeout handler"""
    return render(request, 'core/408.html', status=408)

# Test views for error handlers
def test_404(request):
    """Test 404 error handler"""
    from django.http import Http404
    raise Http404("Test 404 error")

def test_500(request):
    """Test 500 error handler"""
    raise Exception("Test 500 error")

def test_403(request):
    """Test 403 error handler"""
    from django.core.exceptions import PermissionDenied
    raise PermissionDenied("Test 403 error")

def test_400(request):
    """Test 400 error handler"""
    from django.core.exceptions import BadRequest
    raise BadRequest("Test 400 error")

def test_408(request):
    """Test 408 error handler"""
    import time
    # Sleep for a long time to trigger the timeout middleware
    time.sleep(60)
    return HttpResponse("This should never be returned due to timeout")

@login_required
def generate_dynamic_scenario(request, category):
    """Generate a dynamic scenario with multiple questions"""
    user = request.user
    today = timezone.now().date()
    
    # Map UI categories to model categories (same as regular scenarios)
    category_mapping = {
        'career': 'career',
        'financial': 'finance',
        'relationship': 'relationships',
        'time': 'time_management',
        'educational': 'education',
        'health': 'health',
        'ethics': 'ethics',
        'other': 'other'
    } 
    
    # Default to 'other' if category not found
    model_category = category_mapping.get(category.lower(), category.lower())
    
    # Get daily usage tracker
    from .models import DailyUsageTracker
    daily_tracker = DailyUsageTracker.get_for_user(user, today)
    
    # Check if user can generate more scenarios today
    if not daily_tracker.can_generate_scenario():
        max_scenarios = 5 if user.profile.is_premium else 2
        messages.warning(request, f"You've reached your daily limit of {max_scenarios} generated scenarios. Upgrade to premium for more or try again tomorrow.")
        return redirect('core:scenarios')
    
    # Check if user level is high enough for this category (same as regular scenarios)
    level_requirements = {
        'career': 1,
        'finance': 2,
        'relationships': 3,
        'time_management': 4,
        'education': 5,
        'health': 6,
        'ethics': 7,
        'other': 1
    }
    
    required_level = level_requirements.get(model_category, 1)
    if user.profile.level < required_level:
        messages.warning(request, f"You need to reach level {required_level} to generate {model_category.capitalize()} scenarios.")
        return redirect('core:scenarios')
    
    try:
        # Generate the dynamic scenario
        from .utils import generate_dynamic_scenario as create_dynamic_scenario
        scenario = create_dynamic_scenario(user, model_category)
        
        # Update daily tracker
        daily_tracker.scenarios_generated += 1
        daily_tracker.save()
        
        messages.success(request, f"New {scenario.get_category_display()} scenario created successfully!")
        
        # Redirect to the first question
        return redirect('core:dynamic_scenario_question', scenario_id=scenario.id)
        
    except Exception as e:
        print(f"Error generating dynamic scenario: {str(e)}")
        messages.error(request, "There was an error generating your scenario. Please try again.")
        return redirect('core:scenarios')

@login_required
def dynamic_scenario_question(request, scenario_id, question_number=None):
    """Display a question for a dynamic scenario"""
    # Use select_related to reduce database queries
    scenario = get_object_or_404(
        DynamicScenario.objects.select_related('user'), 
        id=scenario_id, 
        user=request.user
    )
    
    # If the scenario is completed, redirect to the report
    if scenario.completed:
        return redirect('core:dynamic_scenario_report', scenario_id=scenario.id)
    
    # Get the current question order from the scenario
    current_question_order = scenario.current_question
    
    # If question_number is provided, verify it's valid
    if question_number is not None:
        # If question_number doesn't match current_question_order, redirect to the correct URL
        if question_number != current_question_order and current_question_order > 0:
            return redirect('core:dynamic_scenario_question_with_number', 
                        scenario_id=scenario.id, 
                        question_number=current_question_order)
    # If no question_number is provided but we have a current question, redirect to the numbered URL
    elif current_question_order > 0:
        return redirect('core:dynamic_scenario_question_with_number', 
                    scenario_id=scenario.id, 
                    question_number=current_question_order)
    
    try:
        # Use select_related to reduce database queries
        question = DynamicScenarioQuestion.objects.select_related('scenario').get(
            scenario=scenario, 
            order=current_question_order
        )
    except DynamicScenarioQuestion.DoesNotExist:
        # If no question exists, generate one
        question = generate_next_question(scenario)
        if not question:
            # If no more questions can be generated, complete the scenario
            # Use cache to prevent repeated report generation
            cache_key = f"completed_scenario_{scenario.id}"
            if not cache.get(cache_key):
                generate_final_report(scenario)
                cache.set(cache_key, True, 86400)  # Cache for 24 hours
            return redirect('core:dynamic_scenario_report', scenario_id=scenario.id)
        
        # Redirect to the numbered URL after generating the first question
        return redirect('core:dynamic_scenario_question_with_number', 
                      scenario_id=scenario.id, 
                      question_number=scenario.current_question)
    
    # Check if this question has already been answered - use prefetch_related for efficiency
    question_with_answers = DynamicScenarioQuestion.objects.filter(
        id=question.id
    ).prefetch_related('answers').first()
    
    has_answer = question_with_answers.answers.exists() if question_with_answers else False
    
    if has_answer:
        # If already answered, move to the next question immediately
        next_question = generate_next_question(scenario)
        if not next_question:
            # If no more questions, generate the final report - use cache
            cache_key = f"completed_scenario_{scenario.id}"
            if not cache.get(cache_key):
                generate_final_report(scenario)
                cache.set(cache_key, True, 86400)  # Cache for 24 hours
            return redirect('core:dynamic_scenario_report', scenario_id=scenario.id)
        
        # Make sure scenario object is updated with the latest state
        scenario.refresh_from_db()
        # Redirect to the numbered URL for the next question
        return redirect('core:dynamic_scenario_question_with_number', 
                      scenario_id=scenario.id, 
                      question_number=scenario.current_question)
    
    # Process form submission
    if request.method == 'POST':
        answer_text = request.POST.get('answer', '').strip()
        
        if not answer_text:
            messages.error(request, "Please provide an answer.")
            if question_number:
                return redirect('core:dynamic_scenario_question_with_number', 
                              scenario_id=scenario.id, 
                              question_number=question_number)
            else:
                return redirect('core:dynamic_scenario_question', scenario_id=scenario.id)
        
        # Evaluate the answer - use cache for similar answers
        cache_key = f"answer_eval_{hashlib.md5(answer_text[:100].encode()).hexdigest()}"
        evaluation = cache.get(cache_key)
        
        if not evaluation:
            evaluation = evaluate_answer(question, answer_text)
            # Cache evaluation results for similar answers (4 hours)
            cache.set(cache_key, evaluation, 14400)
        
        # Save the answer with evaluation in a transaction to ensure consistency
        with transaction.atomic():
            answer = DynamicScenarioAnswer.objects.create(
                question=question,
                answer_text=answer_text,
                rationality_score=evaluation['rationality_score'],
                decisiveness_score=evaluation['decisiveness_score'],
                empathy_score=evaluation['empathy_score'],
                clarity_score=evaluation['clarity_score'],
                feedback=evaluation['feedback']
            )
        
        # Add a message to let the user know their answer was saved
        messages.success(request, "Your answer has been saved. Moving to the next question.")
        
        # Generate the next question
        next_question = generate_next_question(scenario)
        
        if not next_question:
            # If no more questions, generate the final report - use cache
            cache_key = f"completed_scenario_{scenario.id}"
            if not cache.get(cache_key):
                generate_final_report(scenario)
                cache.set(cache_key, True, 86400)  # Cache for 24 hours
            return redirect('core:dynamic_scenario_report', scenario_id=scenario.id)
        
        # The scenario is already updated in generate_next_question
        # Redirect to the numbered URL for the next question
        return redirect('core:dynamic_scenario_question_with_number', 
                      scenario_id=scenario.id, 
                      question_number=scenario.current_question)
    
    context = {
        'scenario': scenario,
        'question': question,
        'progress_percentage': int((current_question_order / scenario.total_questions) * 100),
        'current_question': current_question_order,
        'total_questions': scenario.total_questions
    }
    
    return render(request, 'core/dynamic_scenario_question.html', context)

@login_required
def dynamic_scenario_report(request, scenario_id):
    """Display the final report for a completed dynamic scenario"""
    scenario = get_object_or_404(DynamicScenario, id=scenario_id, user=request.user)
    
    # If the scenario is not completed, redirect to the current question
    if not scenario.completed:
        return redirect('core:dynamic_scenario_question', scenario_id=scenario.id)
    
    # Check if we need to show the success message (only show once)
    show_success_message = False
    session_key = f"dynamic_scenario_{scenario_id}_completed_message_shown"
    if not request.session.get(session_key):
        show_success_message = True
        request.session[session_key] = True
        
        # Show a success message about earned XP and skills
        messages.success(
            request, 
            f"Congratulations! You've completed the scenario and earned 50 XP. "
            f"Your decision-making skills have improved: "
            f"Rationality +{scenario.rationality_score}, "
            f"Decisiveness +{scenario.decisiveness_score}, "
            f"Empathy +{scenario.empathy_score}, "
            f"Clarity +{scenario.clarity_score}"
        )
    
    # Get all questions and answers for reference
    questions = DynamicScenarioQuestion.objects.filter(scenario=scenario).order_by('order')
    question_answers = []
    
    for q in questions:
        answers = q.answers.all()
        answer = answers[0] if answers.exists() else None
        
        if answer:
            question_answers.append({
                'question': q,
                'answer': answer
            })
    
    context = {
        'scenario': scenario,
        'question_answers': question_answers,
        'final_score': scenario.final_score,
        'rationality_score': scenario.rationality_score,
        'decisiveness_score': scenario.decisiveness_score,
        'empathy_score': scenario.empathy_score,
        'clarity_score': scenario.clarity_score,
        'strengths': scenario.strengths,
        'weaknesses': scenario.weaknesses,
        'improvement_plan': scenario.improvement_plan,
        'resources': scenario.resources,
        'show_success_message': show_success_message
    }
    
    return render(request, 'core/dynamic_scenario_report.html', context)

def health_check(request):
    """
    Health check endpoint for monitoring.
    Checks database connection, returns 200 if healthy.
    """
    # Capture start time for response time metric
    start_time = time.time()
    
    # Check database connection
    db_healthy = False
    try:
        # Execute a simple query to check database connectivity
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            db_healthy = result and result[0] == 1
    except Exception as e:
        logger.error(f"Health check database error: {str(e)}")
    
    # Calculate response time
    response_time = time.time() - start_time
    
    # Build health data
    health_data = {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "connected" if db_healthy else "disconnected",
        "timestamp": time.time(),
        "response_time_ms": round(response_time * 1000, 2)
    }
    
    # If unhealthy, set appropriate status code
    status_code = 200 if db_healthy else 503
    
    return JsonResponse(health_data, status=status_code)

def about_view(request):
    """View function for the About Us page."""
    return render(request, 'core/about.html')

def contact_view(request):
    """View function for the Contact page."""
    if request.method == 'POST':
        # Process the contact form if submitted
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        # Create a support issue from the contact form
        if name and email and subject and message:
            try:
                # Create a user account if it doesn't exist
                try:
                    user = User.objects.get(email=email)
                except User.DoesNotExist:
                    # Get or create a user for this message
                    user = request.user if request.user.is_authenticated else None
                
                # Create the support issue
                if user:
                    issue = SupportIssue.objects.create(
                        user=user,
                        title=f"Contact Form: {subject}",
                        description=f"Contact form submission from {name} ({email}):\n\n{message}",
                        status='open',
                        priority='medium'
                    )
                    message="Your message has been sent successfully. We'll get back to you soon!"
                    return render(request, 'core/contact.html', {'message': message, 'status': 200})
                else:
                    messages="We couldn't process your message. Please try again or log in first."
                    return render(request, 'core/contact.html', {'message': messages, 'status': 400})
            except Exception as e:
                messages= f"An error occurred: {str(e)}"
                return render(request, 'core/contact.html', {'message': messages, 'status': 500})
        else:
            messages= "Please fill out all required fields."
            return render(request, 'core/contact.html', {'message': messages, 'status': 400})
    # Render the contact page with a message  
    return render(request, 'core/contact.html')

def privacy_view(request):
    """View function for the Privacy Policy page."""
    return render(request, 'core/privacy.html')

def terms_view(request):
    """View function for the Terms of Service page."""
    return render(request, 'core/terms.html')

def community_public_view(request):
    """View function for the public Community page."""
    return render(request, 'core/community_public.html')

def support_public_view(request):
    """View function for the public Support page."""
    return render(request, 'core/support_public.html')

@login_required
def check_missed_messages(request, user_id):
    """API endpoint to check if client is missing any messages"""
    other_user = get_object_or_404(User, id=user_id)
    current_user = request.user
    
    # Create a unique conversation ID (sorted user IDs to ensure consistency)
    user_ids = sorted([str(current_user.id), str(other_user.id)])
    conversation_id = f"chat_{user_ids[0]}_{user_ids[1]}"
    
    # Get the client's current message count
    try:
        client_message_count = int(request.GET.get('count', 0))
    except ValueError:
        client_message_count = 0
    
    # Get actual message count from DB
    db_message_count = DirectMessage.get_conversation(current_user, other_user).count()
    
    # Check if there's a queue
    queue_length = 0
    if conversation_id in message_queues:
        queue_length = len(message_queues[conversation_id])
    
    # Calculate the maximum expected message count
    expected_message_count = max(db_message_count, queue_length)
    
    # Determine if client needs to reconnect
    reconnect = client_message_count < expected_message_count
    
    return JsonResponse({
        'reconnect': reconnect,
        'client_count': client_message_count,
        'expected_count': expected_message_count
    })

# Add a custom handler for social auth
def social_auth_error(request):
    """Handle social authentication errors."""
    error = request.session.get('social_auth_error')
    
    # Log detailed information about the error
    logger.info(f"Social auth error handler called with error data: {error}")
    
    # Check if we already have error messages
    existing_messages = [m.message for m in messages.get_messages(request)]
    
    if error and not any(error.get('message', '') in str(msg) for msg in existing_messages):
        error_message = error.get('message', 'Authentication error')
        error_backend = error.get('backend', 'unknown')
        error_details = error.get('details', '')
        
        # Log the detailed error for debugging
        logger.error(f"Social auth error: {error_message} (Backend: {error_backend})")
        if error_details:
            logger.error(f"Error details: {error_details}")
        
        # Set message for user
        messages.error(request, f"Authentication error: {error_message}")
        
        # Clear the error from session after using it
        del request.session['social_auth_error']
    elif not existing_messages:
        # Only add a default message if there are no messages
        messages.error(request, "An error occurred during social authentication. This might be because the email address is already registered with another account.")
    
    logger.info("Redirecting to login page after social auth error")
    return redirect('core:login')

@login_required
def notifications_view(request):
    """View for displaying user notifications"""
    user = request.user
    
    # Get all notifications for this user
    notifications = user.notifications.all()[:30]  # Limit to 30 most recent
    
    # Mark all as read if requested
    if request.GET.get('mark_all_read'):
        user.notifications.filter(is_read=False).update(is_read=True)
        messages.success(request, "All notifications marked as read.")
        return redirect('core:notifications')
    
    # Count unread notifications
    unread_count = user.notifications.filter(is_read=False).count()
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count
    }
    
    return render(request, 'core/notifications.html', context)

@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """API endpoint to mark a notification as read"""
    try:
        notification = get_object_or_404(
            Notification, 
            id=notification_id,
            user=request.user
        )
        notification.mark_as_read()
        
        # Clear the unread notifications count cache
        cache_key = f"user_{request.user.id}_unread_notifications_count"
        cache.delete(cache_key)
        
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
def get_unread_notifications_count(request):
    """API endpoint to get unread notifications count"""
    cache_key = f"user_{request.user.id}_unread_notifications_count"
    
    # Try to get from cache first
    unread_count = cache.get(cache_key)
    
    # If not in cache, query database
    if unread_count is None:
        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        # Cache for 5 minutes - notifications don't change that frequently
        cache.set(cache_key, unread_count, 300)
    
    return JsonResponse({
        'unread_count': unread_count
    })

@login_required
@log_request_performance
def community_view(request):
    """View for community page with optimized queries"""
    # Get top members based on activity score - use select_related to reduce queries
    top_members = User.objects.select_related('profile').annotate(
        level=F('profile__level'),
        xp=F('profile__xp_points')
    ).order_by('-profile__level', '-profile__xp_points')[:10]
    
    # Get community chat messages with pagination
    page = request.GET.get('page', 1)
    try:
        page = int(page)
    except ValueError:
        page = 1
    
    # Cache key for community messages
    cache_key = f"community_messages_page_{page}"
    cached_messages = cache.get(cache_key)
    
    if cached_messages:
        chat_messages = cached_messages
    else:
        # Optimize query with select_related and limit to 20 messages per page
        messages_queryset = CommunityMessage.objects.select_related(
            'sender', 'sender__profile'
        ).order_by('-timestamp')
        
        paginator = Paginator(messages_queryset, 20)
        try:
            chat_messages = paginator.page(page)
            # Cache the paginated messages
            cache.set(cache_key, chat_messages, 60)  # Cache for 1 minute
        except (PageNotAnInteger, EmptyPage):
            chat_messages = paginator.page(1)
    
    context = {
        'top_members': top_members,
        'chat_messages': chat_messages,
        'current_page': page,
        'total_pages': chat_messages.paginator.num_pages
    }
    
    return render(request, 'core/community.html', context)

def demo_view(request):
    """View function for the interactive demo page."""
    return render(request, 'core/demo.html')

@csrf_exempt
def razorpay_webhook(request):
    """Webhook endpoint for Razorpay payment events"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)
    
    try:
        # Parse the webhook payload
        data = json.loads(request.body.decode('utf-8'))
        print(f"[WEBHOOK] Received Razorpay webhook: {data.get('event')}")
        
        # Verify webhook signature if available
        webhook_signature = request.headers.get('X-Razorpay-Signature')
        
        if webhook_signature:
            # Verify the webhook signature using your webhook secret
            # razorpay_client.utility.verify_webhook_signature(request.body.decode('utf-8'), webhook_signature, webhook_secret)
            pass
        
        # Extract payment details from the webhook
        event = data.get('event')
        
        if event == 'payment.authorized' or event == 'payment.captured':
            payment_id = data.get('payload', {}).get('payment', {}).get('entity', {}).get('id')
            order_id = data.get('payload', {}).get('payment', {}).get('entity', {}).get('order_id')
            
            if payment_id and order_id:
                # Get the order details to find the user
                try:
                    order = razorpay_client.order.fetch(order_id)
                    user_id = order.get('notes', {}).get('user_id')
                    plan = order.get('notes', {}).get('plan', 'monthly')
                    
                    if user_id:
                        from django.contrib.auth.models import User
                        try:
                            user = User.objects.get(id=user_id)
                            
                            # Determine the subscription duration based on plan
                            duration_days = 30 if plan == 'monthly' else 365
                            
                            # Set the user as premium
                            profile = user.profile
                            profile.payment_method_id = payment_id
                            profile.activate_subscription(plan, duration_days)
                            
                            print(f"[WEBHOOK] Successfully activated premium for user {user.username} via webhook")
                            
                            # Log the activity
                            from core.models import UserActivity
                            UserActivity.log_activity(user, 'webhook_payment_successful', None)
                            
                        except User.DoesNotExist:
                            print(f"[WEBHOOK] User with ID {user_id} not found")
                    else:
                        print(f"[WEBHOOK] No user_id in order notes")
                        
                except Exception as e:
                    print(f"[WEBHOOK] Error processing order {order_id}: {str(e)}")
            
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        print(f"[WEBHOOK] Error processing webhook: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def cancel_subscription_view(request):
    """View for canceling subscriptions"""
    if request.method == 'POST':
        # In a real implementation, you would cancel the subscription in Stripe
        profile = request.user.profile
        profile.cancel_subscription()
        messages.success(request, "Your subscription has been canceled. You will have access until the end of your billing period.")
        return redirect('core:setting')
    
    # Show confirmation page for GET requests
    return render(request, 'core/cancel_subscription.html')
