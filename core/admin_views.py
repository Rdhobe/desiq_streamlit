from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.cache import cache
from django.utils import timezone
from django.db import connection
from django.conf import settings
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Avg, F, ExpressionWrapper, fields
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.contrib import admin
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login
from io import StringIO, BytesIO
import subprocess
import sys
import os
import time
import json
import logging
import threading
import datetime
import csv
import openai
import requests
from django import forms
import psutil
from guardian.shortcuts import get_objects_for_user, assign_perm

from .models import (
    Profile, Scenario, Mentor, PersonalityTest, 
    UserActivity, UserScenarioProgress, UserTestResult, SupportIssue
)

logger = logging.getLogger(__name__)

# Dictionary to store background task status
background_tasks = {}

# Background task function
def run_command_in_background(command, args=None, kwargs=None, user_id=None):
    """Run a management command in the background"""
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}
    
    task_id = f"{command}_{int(time.time())}"
    background_tasks[task_id] = {
        'status': 'running',
        'command': command,
        'started_at': timezone.now(),
        'output': '',
        'completed': False,
        'error': None
    }
    
    try:
        # Capture command output
        out = StringIO()
        sys.stdout = out
        
        # Close any existing connections before running the command
        # This ensures we don't have connection conflicts
        from django.db import connections
        connections.close_all()
        
        # For SQLite specifically, we need to ensure only one connection is active
        if 'sqlite' in connection.vendor:
            # Store original timeout setting if it exists
            original_timeout = None
            original_options = connection.settings_dict.get('OPTIONS', {}).copy()
            
            # Set a longer timeout in the connection settings
            if 'OPTIONS' not in connection.settings_dict:
                connection.settings_dict['OPTIONS'] = {}
            
            # Set 60 seconds timeout
            connection.settings_dict['OPTIONS']['timeout'] = 60
            
            # Run the command with updated settings (which will create a new connection)
            call_command(command, *args, **kwargs)
            
            # Restore original options
            connection.settings_dict['OPTIONS'] = original_options
        else:
            # For other databases, just run the command
            call_command(command, *args, **kwargs)
        
        # Restore stdout
        sys.stdout = sys.__stdout__
        output = out.getvalue()
        
        # Update task status
        background_tasks[task_id]['status'] = 'completed'
        background_tasks[task_id]['completed'] = True
        background_tasks[task_id]['completed_at'] = timezone.now()
        background_tasks[task_id]['output'] = output
        
        # Log activity if user_id is provided
        if user_id:
            try:
                # Create a new connection for this operation
                connections.close_all()
                user = User.objects.get(id=user_id)
                UserActivity.objects.create(
                    user=user,
                    activity_type=f"ran_{command}",
                    created_at=timezone.now()
                )
            except User.DoesNotExist:
                pass
            except Exception as e:
                logger.error(f"Error logging activity: {str(e)}")
            
    except Exception as e:
        # Restore stdout
        sys.stdout = sys.__stdout__
        
        # Update task status
        background_tasks[task_id]['status'] = 'failed'
        background_tasks[task_id]['error'] = str(e)
        background_tasks[task_id]['completed'] = True
        background_tasks[task_id]['completed_at'] = timezone.now()
        
        logger.error(f"Error running background command {command}: {str(e)}")
    
    return task_id

# Check if user is admin
def is_admin(user):
    return user.is_authenticated and user.is_staff

# Admin dashboard view
@user_passes_test(is_admin)
def admin_dashboard(request):
    # Get counts for dashboard stats
    user_count = User.objects.count()
    premium_count = Profile.objects.filter(is_premium=True).count()
    scenario_count = Scenario.objects.count()
    mentor_count = Mentor.objects.count()
    
    # Get open support tickets count
    try:
        open_tickets_count = SupportIssue.objects.filter(status='open').count()
    except:
        open_tickets_count = 0
    
    # Get recent activities
    recent_activities = []
    try:
        # Get admin activities from the database
        admin_activities = UserActivity.objects.filter(
            user__is_staff=True
        ).order_by('-created_at')[:10]
        
        for activity in admin_activities:
            recent_activities.append({
                'message': f"{activity.user.username} performed {activity.activity_type}",
                'timestamp': activity.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })
    except Exception as e:
        logger.error(f"Error fetching admin activities: {str(e)}")
    
    context = {
        'user_count': user_count,
        'premium_count': premium_count,
        'scenario_count': scenario_count,
        'mentor_count': mentor_count,
        'open_tickets_count': open_tickets_count,
        'recent_activities': recent_activities,
    }
    
    return render(request, 'admin/dashboard.html', context)

# Toggle premium status
@user_passes_test(is_admin)
@require_POST
def admin_toggle_premium(request):
    user_id = request.POST.get('user_id')
    if not user_id:
        messages.error(request, "User ID is required.")
        return redirect('core:admin_user_management')
    
    try:
        user = User.objects.get(id=user_id)
        
        # Don't allow toggling premium for staff users
        if user.is_staff:
            messages.error(request, "Cannot change premium status for staff users.")
            return redirect('core:admin_user_management')
        
        # Get or create profile
        profile, created = Profile.objects.get_or_create(user=user)
        
        # Toggle premium status
        profile.is_premium = not profile.is_premium
        profile.save()
        
        # Log activity
        status = "premium" if profile.is_premium else "free"
        UserActivity.objects.create(
            user=request.user,
            activity_type=f"set_user_{status}",
            created_at=timezone.now()
        )
        
        messages.success(request, f"User {user.username} is now {status}.")
        
    except User.DoesNotExist:
        messages.error(request, "User not found.")
    except Exception as e:
        messages.error(request, f"Error toggling premium status: {str(e)}")
        logger.error(f"Error toggling premium status: {str(e)}")
    
    return redirect('core:admin_user_management')

# Run management command
@user_passes_test(is_admin)
def admin_run_command(request, command):
    # Import messages here to ensure it's properly scoped
    from django.contrib import messages
    
    # Map of allowed commands and their display names
    allowed_commands = {
        'add_fake_users': 'Generate Fake Users',
        'add_mentors': 'Add Default Mentors',
        'add_test_scenarios': 'Generate Test Scenarios',
        'add_personality_tests': 'Add Default Personality Tests',
        'add_user_progress': 'Add User Progress',
        'setup_demo_data': 'Setup All Demo Data',
        'create_superuser': 'Create Superuser',
        'add_fake_chats': 'Generate Fake Chat Messages',
    }
    
    # List of commands that should run in the background
    background_commands = ['add_fake_users', 'add_user_progress', 'setup_demo_data', 'add_fake_chats']
    
    if command not in allowed_commands:
        messages.error(request, f"Command '{command}' is not allowed.")
        return redirect('core:admin_dashboard')
    
    # Add command arguments if provided
    args = []
    kwargs = {}
    
    try:
        if command == 'add_fake_users':
            count = request.GET.get('count', 100)
            try:
                count = int(count)
                kwargs['count'] = count
            except ValueError:
                pass
        
        elif command == 'add_test_scenarios':
            count = request.GET.get('count', 30)
            try:
                count = int(count)
                kwargs['count'] = count
            except ValueError:
                pass
        
        elif command == 'add_user_progress':
            min_scenarios = request.GET.get('min_scenarios', 5)
            max_scenarios = request.GET.get('max_scenarios', 20)
            try:
                kwargs['min_scenarios'] = int(min_scenarios)
                kwargs['max_scenarios'] = int(max_scenarios)
            except ValueError:
                pass
        
        elif command == 'create_superuser':
            username = request.GET.get('username', 'admin')
            email = request.GET.get('email', 'admin@example.com')
            password = request.GET.get('password')
            noinput = True
            
            kwargs['username'] = username
            kwargs['email'] = email
            if password:
                kwargs['password'] = password
            kwargs['noinput'] = noinput
        
        elif command == 'add_fake_chats':
            rooms = request.GET.get('rooms', 5)
            messages_count = request.GET.get('messages', 200)
            force = request.GET.get('force', False)
            try:
                kwargs['rooms'] = int(rooms)
                kwargs['messages'] = int(messages_count)
                if force and force.lower() in ('true', '1', 'yes'):
                    kwargs['force'] = True
            except ValueError:
                pass
    except Exception as e:
        logger.error(f"Error parsing command arguments for {command}: {str(e)}")
        messages.error(request, f"Error parsing command arguments: {str(e)}")
        return redirect('core:admin_dashboard')
    
    # Special handling for setup_demo_data which is a shell script
    if command == 'setup_demo_data':
        # Make script executable
        script_path = os.path.join(os.getcwd(), 'setup_demo_data.sh')
        try:
            # For Windows, use python to run the script
            if os.name == 'nt':
                process = subprocess.Popen(
                    ['python', '-c', f"import subprocess; subprocess.call(['{script_path}'])"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            else:
                # Make executable first
                subprocess.call(['chmod', '+x', script_path])
                process = subprocess.Popen(
                    [script_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            
            stdout, stderr = process.communicate()
            output = stdout + "\n" + stderr
            messages.success(request, f"Successfully ran {allowed_commands[command]}.")
            
            # Log activity
            UserActivity.objects.create(
                user=request.user,
                activity_type=f"ran_{command}",
                created_at=timezone.now()
            )
            
            # Store output in session for display
            request.session['command_output'] = output
            
        except Exception as e:
            messages.error(request, f"Error running {allowed_commands[command]}: {str(e)}")
            logger.error(f"Error running {command}: {str(e)}")
        
        return redirect('core:admin_command_output')
    
    # Check if command should run in the background
    if command in background_commands:
        try:
            # Start the command in a background thread
            thread = threading.Thread(
                target=run_command_in_background,
                args=(command,),
                kwargs={'args': args, 'kwargs': kwargs, 'user_id': request.user.id}
            )
            thread.daemon = True
            thread.start()
            
            messages.success(request, f"{allowed_commands[command]} is running in the background. This may take a few minutes.")
        except Exception as e:
            logger.error(f"Error starting background thread for {command}: {str(e)}")
            messages.error(request, f"Error starting background process: {str(e)}")
        
        return redirect('core:admin_dashboard')
    
    try:
        # For non-background commands, run normally
        out = StringIO()
        sys.stdout = out
        
        # Run Django management command
        call_command(command, *args, **kwargs)
        
        # Restore stdout
        sys.stdout = sys.__stdout__
        output = out.getvalue()
        
        # Log activity
        UserActivity.objects.create(
            user=request.user,
            activity_type=f"ran_{command}",
            created_at=timezone.now()
        )
        
        messages.success(request, f"Successfully ran {allowed_commands[command]}.")
        
        # Store output in session for display
        request.session['command_output'] = output
        
        return redirect('core:admin_command_output')
        
    except Exception as e:
        # Restore stdout
        sys.stdout = sys.__stdout__
        
        messages.error(request, f"Error running {allowed_commands[command]}: {str(e)}")
        logger.error(f"Error running {command}: {str(e)}")
        
        return redirect('core:admin_dashboard')

# Display command output
@user_passes_test(is_admin)
def admin_command_output(request):
    output = request.session.get('command_output', 'No output available.')
    
    context = {
        'output': output,
    }
    
    return render(request, 'admin/command_output.html', context)

# Backup database
@user_passes_test(is_admin)
def admin_backup_database(request):
    try:
        # Run backup script
        script_path = os.path.join(os.getcwd(), 'backup_db.sh')
        
        # For Windows, use python to run the script
        if os.name == 'nt':
            process = subprocess.Popen(
                ['python', '-c', f"import subprocess; subprocess.call(['{script_path}'])"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        else:
            # Make executable first
            subprocess.call(['chmod', '+x', script_path])
            process = subprocess.Popen(
                [script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        
        stdout, stderr = process.communicate()
        output = stdout + "\n" + stderr
        
        # Log activity
        UserActivity.objects.create(
            user=request.user,
            activity_type="database_backup",
            created_at=timezone.now()
        )
        
        messages.success(request, "Database backup completed successfully.")
        
        # Store output in session for display
        request.session['command_output'] = output
        
        return redirect('core:admin_command_output')
        
    except Exception as e:
        messages.error(request, f"Error backing up database: {str(e)}")
        logger.error(f"Error backing up database: {str(e)}")
        
        return redirect('core:admin_dashboard')

# Clear cache
@user_passes_test(is_admin)
def admin_clear_cache(request):
    try:
        # Clear Django cache
        cache.clear()
        
        # Log activity
        UserActivity.objects.create(
            user=request.user,
            activity_type="clear_cache",
            created_at=timezone.now()
        )
        
        messages.success(request, "Cache cleared successfully.")
        
    except Exception as e:
        messages.error(request, f"Error clearing cache: {str(e)}")
        logger.error(f"Error clearing cache: {str(e)}")
    
    return redirect('core:admin_dashboard')

# System status
@user_passes_test(is_admin)
def admin_system_status(request):
    # Get system status information
    status = {}
    
    # Database connection check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            status['database'] = {
                'connected': True,
            'engine': connection.vendor,
                'version': connection.mysql_version if hasattr(connection, 'mysql_version') else 
                          connection.postgresql_version if hasattr(connection, 'postgresql_version') else
                          'Unknown'
            }
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        status['database'] = {
            'connected': False,
            'engine': connection.vendor,
            'error': str(e)
        }
    
    # Cache check
    try:
        cache_key = 'admin_system_status_test'
        cache_value = f'test_{time.time()}'
        cache.set(cache_key, cache_value, 10)
        retrieved_value = cache.get(cache_key)
        
        status['cache'] = {
            'working': retrieved_value == cache_value,
            'backend': settings.CACHES['default']['BACKEND'],
        }
    except Exception as e:
        logger.error(f"Cache error: {str(e)}")
        status['cache'] = {
            'working': False,
            'error': str(e)
        }
    
    # File storage check
    try:
        # Check if media and static directories are writable
        media_writable = os.access(settings.MEDIA_ROOT, os.W_OK)
        static_writable = os.access(settings.STATIC_ROOT, os.W_OK)
        
        status['storage'] = {
            'media_writable': media_writable,
            'static_writable': static_writable,
            'media_path': settings.MEDIA_ROOT,
            'static_path': settings.STATIC_ROOT,
        }
    except Exception as e:
        logger.error(f"Storage check error: {str(e)}")
        status['storage'] = {
            'error': str(e)
        }
    
    # System usage stats
    try:
        status['system'] = {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
        }
    except Exception as e:
        logger.error(f"System stats error: {str(e)}")
        status['system'] = {
            'error': str(e)
        }
    
    # Django version & Python version
    status['versions'] = {
        'django': django.get_version(),
        'python': sys.version,
    }
    
    # Logs check (last few lines)
    try:
        log_file = 'logs/app.log'  # Adjust path as needed
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                # Get last 10 lines
                log_lines = f.readlines()[-10:]
                status['logs'] = {
                    'last_lines': log_lines,
                    'log_file': log_file,
                }
        else:
            status['logs'] = {
                'error': f"Log file not found: {log_file}"
        }
    except Exception as e:
        logger.error(f"Log check error: {str(e)}")
        status['logs'] = {
            'error': str(e)
        }
    
    # Query performance stats if using Django Debug Toolbar
    status['query_stats'] = {
        'note': 'Install Django Debug Toolbar for detailed query information'
    }
    
    # Add external services checks (if applicable)
    
    return render(request, 'admin/system_status.html', {'status': status})

# Admin user management
@user_passes_test(is_admin)
def admin_user_management(request):
    # Get all users with their profiles
    users = User.objects.all().select_related('profile')
    
    context = {
        'users': users,
    }
    
    return render(request, 'admin/user_management.html', context)

# Admin mentor management
@user_passes_test(is_admin)
def admin_mentor_management(request):
    # Get search query
    search_query = request.GET.get('search', '')
    
    # Get all mentors with filtering if search is provided
    if search_query:
        mentors = Mentor.objects.filter(
            Q(name__icontains=search_query) | 
            Q(specialty__icontains=search_query) |
            Q(description__icontains=search_query)
        ).order_by('name')
    else:
        mentors = Mentor.objects.all().order_by('name')
    
    # Set up pagination
    paginator = Paginator(mentors, 10)  # Show 10 mentors per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'mentors': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': page_obj,
    }
    
    return render(request, 'admin/mentor_management.html', context)

# Toggle mentor active status
@user_passes_test(is_admin)
@require_POST
def admin_toggle_mentor_status(request):
    mentor_id = request.POST.get('mentor_id')
    if not mentor_id:
        messages.error(request, "Mentor ID is required.")
        return redirect('core:admin_mentor_management')
    
    try:
        mentor = Mentor.objects.get(id=mentor_id)
        
        # Toggle active status
        mentor.is_active = not mentor.is_active
        mentor.save()
        
        # Log activity
        status = "active" if mentor.is_active else "inactive"
        UserActivity.objects.create(
            user=request.user,
            activity_type=f"set_mentor_{status}",
            created_at=timezone.now()
        )
        
        messages.success(request, f"Mentor {mentor.name} is now {status}.")
        
    except Mentor.DoesNotExist:
        messages.error(request, "Mentor not found.")
    except Exception as e:
        messages.error(request, f"Error toggling mentor status: {str(e)}")
        logger.error(f"Error toggling mentor status: {str(e)}")
    
    return redirect('core:admin_mentor_management')

# Admin scenario management
@user_passes_test(is_admin)
def admin_scenario_management(request):
    # Get search query and category filter
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    
    # Start with all scenarios
    scenarios = Scenario.objects.all()
    
    # Apply filters if provided
    if search_query:
        scenarios = scenarios.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    if category_filter:
        scenarios = scenarios.filter(category=category_filter)
    
    # Order by most recent first
    scenarios = scenarios.order_by('-created_at')
    
    # Set up pagination
    paginator = Paginator(scenarios, 10)  # Show 10 scenarios per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'scenarios': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': page_obj,
    }
    
    return render(request, 'admin/scenario_management.html', context)

# Toggle scenario active status
@user_passes_test(is_admin)
@require_POST
def admin_toggle_scenario_status(request):
    scenario_id = request.POST.get('scenario_id')
    if not scenario_id:
        messages.error(request, "Scenario ID is required.")
        return redirect('core:admin_scenario_management')
    
    try:
        scenario = Scenario.objects.get(id=scenario_id)
        
        # Toggle active status
        scenario.is_active = not scenario.is_active
        scenario.save()
        
        # Log activity
        status = "active" if scenario.is_active else "inactive"
        UserActivity.objects.create(
            user=request.user,
            activity_type=f"set_scenario_{status}",
            created_at=timezone.now()
        )
        
        messages.success(request, f"Scenario '{scenario.title}' is now {status}.")
        
    except Scenario.DoesNotExist:
        messages.error(request, "Scenario not found.")
    except Exception as e:
        messages.error(request, f"Error toggling scenario status: {str(e)}")
        logger.error(f"Error toggling scenario status: {str(e)}")
    
    return redirect('core:admin_scenario_management')

# Admin personality test management
@user_passes_test(is_admin)
def admin_personality_test_management(request):
    # Get search query
    search_query = request.GET.get('search', '')
    
    # Get all personality tests with filtering if search is provided
    if search_query:
        tests = PersonalityTest.objects.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query)
        ).order_by('title')
    else:
        tests = PersonalityTest.objects.all().order_by('title')
    
    # Set up pagination
    paginator = Paginator(tests, 10)  # Show 10 tests per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'tests': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': page_obj,
    }
    
    return render(request, 'admin/personality_test_management.html', context)

# Custom admin login view
def admin_login(request):
    """Custom admin login view that redirects to admin dashboard"""
    from django.contrib.auth import authenticate, login
    from django.shortcuts import redirect, render
    from django.contrib.auth.forms import AuthenticationForm
    from django.contrib import messages
    from django import forms
    
    # Custom form for admin login that accepts both username and email
    class AdminAuthenticationForm(AuthenticationForm):
        username = forms.CharField(label="Username or Email")

    # If user is already authenticated, redirect to admin dashboard
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('core:admin_dashboard')
    
    if request.method == 'POST':
        form = AdminAuthenticationForm(request, data=request.POST)
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            # Authenticate user - our backend will handle email authentication
            user = authenticate(request=request, username=username, password=password)
            
            if user is not None and user.is_staff:
                login(request, user)
                logger.info(f"Admin login successful: {user.username}")
                return redirect('core:admin_dashboard')
            elif user is not None:
                # User is authenticated but not staff
                logger.warning(f"Non-staff user attempted admin login: {user.username}")
                messages.error(request, "You don't have admin privileges.")
            else:
                # Authentication failed
                logger.warning(f"Failed admin login attempt for: {username}")
                messages.error(request, "Invalid username/email or password.")
        else:
            messages.error(request, "Please provide both username/email and password.")
            
        # If authentication failed, redisplay the form with error messages
        context = {
            'form': form,
            'title': 'Admin Log in',
            'site_title': 'DesiQ Admin',
            'site_header': 'DesiQ Administration',
        }
        return render(request, 'admin/login.html', context)
    else:
        # Display empty form for GET requests
        form = AdminAuthenticationForm()
        context = {
            'form': form,
            'title': 'Admin Log in',
            'site_title': 'DesiQ Admin',
            'site_header': 'DesiQ Administration',
        }
        return render(request, 'admin/login.html', context)

# New view to check background task status
@user_passes_test(is_admin)
def admin_background_tasks(request):
    """View to display status of background tasks"""
    context = {
        'tasks': background_tasks
    }
    return render(request, 'admin/background_tasks.html', context)

# Enhanced admin analytics dashboard
@user_passes_test(is_admin)
def admin_analytics_dashboard(request):
    # Get the time range filter
    time_range = request.GET.get('time_range', '30')  # Default to 30 days
    
    try:
        days = int(time_range)
    except ValueError:
        days = 30
    
    # Calculate date range
    end_date = timezone.now()
    start_date = end_date - datetime.timedelta(days=days)
    
    # Prepare chart data
    user_growth_data = get_user_growth_data(start_date, end_date)
    scenario_completion_data = get_scenario_completion_data(start_date, end_date)
    premium_conversion_data = get_premium_conversion_data(start_date, end_date)
    active_users_data = get_active_users_data(start_date, end_date)
    
    # Get top scenarios by completion
    top_scenarios = Scenario.objects.annotate(
        completion_count=Count('userscenarioprogress', filter=Q(userscenarioprogress__completed=True))
    ).order_by('-completion_count')[:10]
    
    # Get conversion metrics
    total_users = User.objects.filter(date_joined__gte=start_date).count()
    premium_users = Profile.objects.filter(
        user__date_joined__gte=start_date,
        is_premium=True
    ).count()
    
    conversion_rate = 0
    if total_users > 0:
        conversion_rate = (premium_users / total_users) * 100
    
    # Get activity distribution by type
    activity_distribution = UserActivity.objects.filter(
        created_at__gte=start_date
    ).values('activity_type').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Prepare context
    context = {
        'time_range': time_range,
        'user_growth_data': json.dumps(user_growth_data),
        'scenario_completion_data': json.dumps(scenario_completion_data),
        'premium_conversion_data': json.dumps(premium_conversion_data),
        'active_users_data': json.dumps(active_users_data),
        'top_scenarios': top_scenarios,
        'conversion_rate': round(conversion_rate, 2),
        'total_users_period': total_users,
        'premium_users_period': premium_users,
        'activity_distribution': activity_distribution,
    }
    
    return render(request, 'admin/analytics_dashboard.html', context)

def get_user_growth_data(start_date, end_date):
    """Get data for user growth chart"""
    # Group by day for shorter periods, by week for medium periods, by month for longer
    days_diff = (end_date - start_date).days
    
    if days_diff <= 31:
        # Daily for up to a month
        trunc_func = TruncDay
        date_format = '%Y-%m-%d'
    elif days_diff <= 90:
        # Weekly for up to 3 months
        trunc_func = TruncWeek
        date_format = '%Y-W%W'
    else:
        # Monthly for longer periods
        trunc_func = TruncMonth
        date_format = '%Y-%m'
    
    # Get user signups grouped by the appropriate time period
    user_signups = User.objects.filter(
        date_joined__range=(start_date, end_date)
    ).annotate(
        period=trunc_func('date_joined')
    ).values('period').annotate(
        count=Count('id')
    ).order_by('period')
    
    # Format data for Chart.js
    labels = []
    data = []
    
    # Convert to dict for easier lookup
    signup_dict = {item['period'].strftime(date_format): item['count'] for item in user_signups}
    
    # Generate all periods in range
    current_date = start_date
    while current_date <= end_date:
        period_key = current_date.strftime(date_format)
        labels.append(period_key)
        data.append(signup_dict.get(period_key, 0))
        
        # Increment based on period type
        if days_diff <= 31:
            current_date += datetime.timedelta(days=1)
        elif days_diff <= 90:
            current_date += datetime.timedelta(days=7)
        else:
            # Add a month (approximate)
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
    
    return {'labels': labels, 'data': data}

def get_scenario_completion_data(start_date, end_date):
    """Get data for scenario completion chart"""
    # Get completed scenarios grouped by day
    completed_scenarios = UserScenarioProgress.objects.filter(
        completed=True,
        completed_at__range=(start_date, end_date)
        ).annotate(
        day=TruncDay('completed_at')
    ).values('day').annotate(
            count=Count('id')
    ).order_by('day')
    
    # Format data for Chart.js
    labels = []
    data = []
    
    # Convert to dict for easier lookup
    completion_dict = {item['day'].strftime('%Y-%m-%d'): item['count'] for item in completed_scenarios}
    
    # Generate all days in range
    current_date = start_date
    while current_date <= end_date:
        day_key = current_date.strftime('%Y-%m-%d')
        labels.append(day_key)
        data.append(completion_dict.get(day_key, 0))
        current_date += datetime.timedelta(days=1)
    
    return {'labels': labels, 'data': data}

def get_premium_conversion_data(start_date, end_date):
    """Get data for premium conversion chart"""
    # This is a simplified version - in a real app, you'd track when users convert to premium
    # For now, we'll just use the date_joined and assume premium status was set at that time
    premium_users = Profile.objects.filter(
        is_premium=True,
        user__date_joined__range=(start_date, end_date)
        ).annotate(
        day=TruncDay('user__date_joined')
    ).values('day').annotate(
            count=Count('id')
    ).order_by('day')
    
    # Format data for Chart.js
    labels = []
    premium_data = []
    
    # Convert to dict for easier lookup
    premium_dict = {item['day'].strftime('%Y-%m-%d'): item['count'] for item in premium_users}
    
    # Generate all days in range
    current_date = start_date
    while current_date <= end_date:
        day_key = current_date.strftime('%Y-%m-%d')
        labels.append(day_key)
        premium_data.append(premium_dict.get(day_key, 0))
        current_date += datetime.timedelta(days=1)
    
    return {'labels': labels, 'data': premium_data}

def get_active_users_data(start_date, end_date):
    """Get data for active users chart (users with activity)"""
    # Get active users by day
    active_users = UserActivity.objects.filter(
        created_at__range=(start_date, end_date)
    ).annotate(
        day=TruncDay('created_at')
    ).values('day').annotate(
        unique_users=Count('user', distinct=True)
    ).order_by('day')
    
    # Format data for Chart.js
    labels = []
    data = []
    
    # Convert to dict for easier lookup
    active_dict = {item['day'].strftime('%Y-%m-%d'): item['unique_users'] for item in active_users}
    
    # Generate all days in range
    current_date = start_date
    while current_date <= end_date:
        day_key = current_date.strftime('%Y-%m-%d')
        labels.append(day_key)
        data.append(active_dict.get(day_key, 0))
        current_date += datetime.timedelta(days=1)
    
    return {'labels': labels, 'data': data}

@user_passes_test(is_admin)
def admin_export_data(request, data_type):
    """Export data in CSV format"""
    # Set up response as a CSV file
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{data_type}_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    
    # Export different data based on type
    if data_type == 'users':
        # Export users data
        writer.writerow(['Username', 'Email', 'Date Joined', 'Last Login', 'Is Premium', 'XP Points', 'Level'])
        
        users = User.objects.select_related('profile').all()
        for user in users:
            premium = False
            xp_points = 0
            level = 0
            
            if hasattr(user, 'profile'):
                premium = user.profile.is_premium
                xp_points = user.profile.xp_points
                level = user.profile.level
            
            writer.writerow([
                user.username,
                user.email,
                user.date_joined,
                user.last_login or '',
                premium,
                xp_points,
                level
            ])
            
    elif data_type == 'scenarios':
        # Export scenarios data
        writer.writerow(['Title', 'Category', 'Difficulty', 'XP Reward', 'Completion Count', 'Created At'])
        
        scenarios = Scenario.objects.annotate(
            completion_count=Count('userscenarioprogress', filter=Q(userscenarioprogress__completed=True))
        ).all()
        
        for scenario in scenarios:
            writer.writerow([
                scenario.title,
                scenario.category,
                scenario.difficulty,
                scenario.xp_reward,
                scenario.completion_count,
                scenario.created_at
            ])
            
    elif data_type == 'personality_tests':
        # Export personality test results
        writer.writerow(['Test Name', 'User', 'Result Type', 'Created At'])
        
        results = UserTestResult.objects.select_related('user', 'test', 'result').all()
        
        for result in results:
            writer.writerow([
                result.test.name,
                result.user.username,
                result.result.result_type if result.result else '',
                result.created_at
            ])
    
    return response

@user_passes_test(is_admin)
def admin_ai_summarize_ticket(request, ticket_id):
    """Use AI to summarize a support ticket"""
    ticket = get_object_or_404(SupportIssue, id=ticket_id)
    
    # Check if we have an OpenAI API key
    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not api_key:
        messages.error(request, "OpenAI API key not configured. Add OPENAI_API_KEY in settings.")
        return redirect('core:admin_support_tickets')
    
    try:
        openai.api_key = api_key
        
        # Prepare the content to summarize
        content = f"Title: {ticket.title}\n\nDescription: {ticket.description}"
        if content and len(content) > 20:  # Only if there's meaningful content
            # Use OpenAI to generate a summary
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant that summarizes support tickets briefly and identifies key issues."},
                    {"role": "user", "content": f"Please summarize this support ticket in 50 words or less, identifying the main user issue:\n\n{content}"}
                ],
                max_tokens=100
            )
            
            # Get the summary
            summary = response.choices[0].message['content'].strip()
            
            # Store the summary in the session for display
            request.session['ticket_summary'] = {
                'ticket_id': ticket_id,
                'summary': summary
            }
            
            messages.success(request, "AI summary generated successfully")
        else:
            messages.warning(request, "Ticket content too short for summarization")
    except Exception as e:
        logger.error(f"Error generating AI summary: {str(e)}")
        messages.error(request, f"Error generating summary: {str(e)}")
    
    return redirect('core:admin_support_tickets')

# Enhanced support tickets view
@user_passes_test(is_admin)
def admin_support_tickets(request):
    # Get filters from request
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    
    # Base query
    tickets = SupportIssue.objects.all()
    
    # Apply filters
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    
    if search_query:
        tickets = tickets.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )
    
    # Order by latest first
    tickets = tickets.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(tickets, 15)  # Show 15 tickets per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get any AI summary from session
    ticket_summary = request.session.pop('ticket_summary', None)
    
    context = {
        'tickets': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'ticket_summary': ticket_summary,
    }
    
    return render(request, 'admin/support_tickets.html', context)

# Role-based permissions admin
@user_passes_test(is_admin)
def admin_manage_permissions(request):
    """Manage role-based permissions"""
    # Get all staff users
    staff_users = User.objects.filter(is_staff=True)
    
    # Define permission sets (roles)
    permission_roles = {
        'content_editor': [
            'view_scenario', 'add_scenario', 'change_scenario', 'delete_scenario',
            'view_mentor', 'add_mentor', 'change_mentor', 'delete_mentor',
            'view_personalitytest', 'add_personalitytest', 'change_personalitytest', 'delete_personalitytest',
        ],
        'support_agent': [
            'view_supportissue', 'change_supportissue',
            'view_issuecomment', 'add_issuecomment', 'change_issuecomment',
        ],
        'analytics_viewer': [
            'view_useractivity', 'view_userscenariosprogress', 'view_usertestresult',
        ],
        'system_admin': [
            'view_user', 'add_user', 'change_user',
            'view_group', 'add_group', 'change_group',
        ]
    }
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        role = request.POST.get('role')
        action = request.POST.get('action')  # 'assign' or 'revoke'
        
        if user_id and role and role in permission_roles:
            try:
                user = User.objects.get(id=user_id)
                permissions = permission_roles[role]
                
                for perm in permissions:
                    app_label, codename = perm.split('_', 1)
                    if action == 'assign':
                        user.user_permissions.add(f"{app_label}.{codename}")
                    elif action == 'revoke':
                        user.user_permissions.remove(f"{app_label}.{codename}")
                
                messages.success(request, f"Successfully {'assigned' if action == 'assign' else 'revoked'} {role} permissions for {user.username}")
                
                # Log activity
                UserActivity.objects.create(
                    user=request.user,
                    activity_type=f"{action}_{role}_role",
                    created_at=timezone.now()
                )
                
            except User.DoesNotExist:
                messages.error(request, "User not found")
            except Exception as e:
                logger.error(f"Error managing permissions: {str(e)}")
                messages.error(request, f"Error: {str(e)}")
    
    # Prepare context with users and their roles
    users_with_roles = []
    for user in staff_users:
        user_roles = []
        for role, perms in permission_roles.items():
            # Check if user has all permissions for this role
            has_all_perms = all(user.has_perm(perm) for perm in perms)
            if has_all_perms:
                user_roles.append(role)
        
        users_with_roles.append({
            'user': user,
            'roles': user_roles
        })
    
    context = {
        'users_with_roles': users_with_roles,
        'available_roles': permission_roles.keys(),
    }
    
    return render(request, 'admin/manage_permissions.html', context)

# Admin REPL Console (restricted to superusers)
@user_passes_test(lambda u: u.is_superuser)
def admin_repl_console(request):
    """Admin REPL console for executing Python code (superuser only)"""
    result = None
    error = None
    
    if request.method == 'POST':
        code = request.POST.get('code', '')
        
        if code:
            # Log this action for security
            logger.warning(f"REPL console used by {request.user.username}")
            
            # Execute the code in a secure manner
            try:
                # Create a string buffer to capture output
                stdout_buffer = StringIO()
                stderr_buffer = StringIO()
                
                # Store original stdout and stderr
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                
                # Redirect stdout and stderr
                sys.stdout = stdout_buffer
                sys.stderr = stderr_buffer
                
                # Create a safe local context
                local_vars = {'request': request}
                
                # Execute the code
                exec(code, {'__builtins__': __builtins__}, local_vars)
                
                # Get output
                result = stdout_buffer.getvalue()
                error = stderr_buffer.getvalue()
                
                # Restore stdout and stderr
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                
            except Exception as e:
                error = str(e)
                logger.error(f"REPL console error: {error}")
    
    context = {
        'result': result,
        'error': error,
    }
    
    return render(request, 'admin/repl_console.html', context) 