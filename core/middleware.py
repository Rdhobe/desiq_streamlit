import time
import threading
import logging
import json
import asyncio
import os
import sys
import traceback
import re
import psutil
import datetime
from functools import wraps

from django.http import HttpResponse, HttpResponseServerError, JsonResponse
from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db import close_old_connections, connection, transaction, reset_queries
from django.contrib.auth.models import AnonymousUser, User
from django.middleware.common import MiddlewareMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.core.cache import cache
from django.contrib.sessions.models import Session

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from channels.auth import get_user, AuthMiddlewareStack

from social_core.exceptions import SocialAuthBaseException, AuthException

# Add import for the social auth fix
try:
    from social_core.backends.utils import BACKENDSCACHE
    from social_core.backends.google import GoogleOAuth2
    from social_core.backends.github import GithubOAuth2
    SOCIAL_AUTH_IMPORTS_AVAILABLE = True
except ImportError:
    SOCIAL_AUTH_IMPORTS_AVAILABLE = False

logger = logging.getLogger(__name__)

# Import resource module if on Unix/Linux (not available on Windows)
is_windows = sys.platform.startswith('win')
if not is_windows:
    import resource
else:
    # Mock resource module for Windows
    class ResourceMock:
        def getrusage(self, *args, **kwargs):
            return type('obj', (object,), {'ru_maxrss': 0})
        
        def RUSAGE_SELF(self):
            return 0
    
    resource = ResourceMock()

# Custom HTTP response classes
class HttpResponseTooManyRequests(HttpResponse):
    status_code = 429

class HttpResponseRequestTimeout(HttpResponse):
    status_code = 408

class HttpResponseProcessTerminated(HttpResponse):
    status_code = 503

@database_sync_to_async
def get_user(session_key):
    try:
        session = Session.objects.get(session_key=session_key)
        session_data = session.get_decoded()
        user_id = session_data.get('_auth_user_id')
        user = User.objects.get(id=user_id)
        return user
    except (Session.DoesNotExist, User.DoesNotExist, KeyError):
        return AnonymousUser()

class WebSocketAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        # Close old database connections to prevent usage of timed out connections
        close_old_connections()
        
        # Get the session from cookies
        cookies = {}
        headers = dict(scope.get('headers', []))
        
        if b'cookie' in headers:
            cookie_str = headers[b'cookie'].decode()
            cookie_pairs = cookie_str.split('; ')
            for pair in cookie_pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    cookies[key] = value
        
        session_key = cookies.get('sessionid', '')
        
        # Get the user
        if session_key:
            scope['user'] = await get_user(session_key)
        else:
            scope['user'] = AnonymousUser()
            
        return await super().__call__(scope, receive, send)

def WebSocketAuthMiddlewareStack(inner):
    return WebSocketAuthMiddleware(AuthMiddlewareStack(inner))

class ExceptionMiddleware:
    """
    Middleware to handle exceptions gracefully and log them
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            # Wrap the entire request in a try-except block
            response = self.get_response(request)
            return response
        except Exception as e:
            # Log and handle uncaught exceptions
            return self.handle_exception(request, e)

    def process_exception(self, request, exception):
        """
        Process exceptions and log them with detailed information
        """
        return self.handle_exception(request, exception)
        
    def handle_exception(self, request, exception):
        """
        Centralized exception handling
        """
        # Log the exception with traceback
        logger.error(
            f"Exception caught in {request.path}\n"
            f"Method: {request.method}\n"
            f"User: {request.user}\n"
            f"Exception: {str(exception)}\n"
            f"Traceback: {traceback.format_exc()}"
        )

        # Close any broken DB connections
        try:
            connection.close()
        except:
            pass

        # In production, return a custom 500 page
        if not settings.DEBUG:
            try:
                # First try rendering the 500 template
                from django.template.loader import render_to_string
                from django.http import HttpResponseServerError
                
                # Try to find the template directly
                template_path = os.path.join(settings.BASE_DIR, 'core', 'templates', 'core', '500.html')
                
                # Log template information for debugging
                logger.error(f"Trying to render 500 template: {template_path}")
                logger.error(f"Template exists: {os.path.exists(template_path)}")
                
                # First try to use Django's template renderer
                try:
                    html = render_to_string('core/500.html', request=request)
                    return HttpResponseServerError(html)
                except Exception as template_error:
                    logger.error(f"Error rendering 500 template: {str(template_error)}")
                    
                    # Fallback to direct file reading if template rendering fails
                    try:
                        with open(template_path, 'r') as f:
                            html = f.read()
                        return HttpResponseServerError(html)
                    except Exception as file_error:
                        logger.error(f"Error reading 500 template file: {str(file_error)}")
                        
                        # Last resort - return a basic 500 response
                        return HttpResponseServerError(
                            "<html><body><h1>500 Server Error</h1><p>Sorry, something went wrong on our end.</p></body></html>"
                        )
            except Exception as render_error:
                logger.error(f"Error in error handling: {str(render_error)}")
                return HttpResponseServerError(
                    "<html><body><h1>500 Server Error</h1><p>Sorry, something went wrong on our end.</p></body></html>"
                )
        
        # In debug mode, let Django's debug page handle it
        return None

class DatabaseConnectionMiddleware:
    """
    Middleware to handle database connection issues with PostgreSQL
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.max_retries = 3
        self.check_interval = 100  # Check connection every 100 requests
        self.slow_query_threshold = 0.5  # Log queries slower than 500ms
        
        # Initialize connection pool monitoring
        self.total_connections = 0
        self.total_queries = 0
        self.last_reset = timezone.now()

    def __call__(self, request):
        # Get request counter from cache to avoid checking on every request
        from django.core.cache import cache
        counter_key = 'db_connection_check_counter'
        counter = cache.get(counter_key, 0)
        
        # Close any stale connections before processing
        close_old_connections()
        
        # Only test connection periodically to reduce overhead
        should_check = (counter % self.check_interval == 0)
        
        # Initialize query tracking
        if settings.DEBUG:
            # Reset connection.queries
            reset_queries()
            start_time = time.time()
        
        # Try to process the request, with retries for connection issues
        for attempt in range(self.max_retries):
            try:
                # Check connection if needed
                if should_check and not self._check_connection():
                    logger.warning(f"Connection check failed on attempt {attempt+1}, reconnecting...")
                    connection.close()
                    connection.connect()
                
                # Process the request inside a transaction
                response = self.get_response(request)
                
                # Increment counter
                cache.set(counter_key, counter + 1, 3600)  # Store for 1 hour
                
                # Log slow queries in debug mode
                if settings.DEBUG:
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    # Only analyze queries for slower requests
                    if duration > self.slow_query_threshold:
                        try:
                            slowest_queries = self._find_slow_queries(connection.queries, 0.1)  # Queries slower than 100ms
                            if slowest_queries:
                                logger.warning(
                                    f"Slow request: {request.path} ({duration:.2f}s) - "
                                    f"Found {len(slowest_queries)} slow queries"
                                )
                                for i, query in enumerate(slowest_queries[:5]):  # Show up to 5 slow queries
                                    logger.warning(f"Slow query {i+1}: {query['time']:.2f}s - {query['sql'][:100]}...")
                        except Exception as e:
                            logger.error(f"Error analyzing slow queries: {str(e)}")
                
                # All good, close connections that are no longer needed
                close_old_connections()
                return response
                
            except Exception as e:
                # Look for connection-related errors
                error_msg = str(e).lower()
                is_connection_error = any(err in error_msg for err in [
                    'connection already closed', 'connection not open',
                    'terminating connection', 'operational error', 
                    'server closed the connection', 'connection refused',
                    'could not connect', 'timeout', 'deadlock',
                    'current transaction is aborted'
                ])
                
                if is_connection_error and attempt < self.max_retries - 1:
                    logger.warning(f"Database connection error (attempt {attempt+1}/{self.max_retries}): {str(e)}")
                    # Try to close and reset the connection
                    try:
                        connection.close()
                    except Exception:
                        pass
                    
                    # Pause briefly before retry (exponential backoff)
                    time.sleep(0.5 * (attempt + 1))
                    continue
                else:
                    # Either it's not a connection error or we've exhausted retries
                    logger.error(f"Database error: {str(e)}")
                    # Close any broken connections
                    try:
                        connection.close()
                    except Exception:
                        pass
                    
                    # Return a custom error page in production
                    if not settings.DEBUG:
                        return HttpResponseServerError(
                            render_to_string('core/500.html', request=request)
                        )
                    raise
        
        # If we get here, we've exhausted retries
        logger.critical("Exhausted database connection retries")
        return HttpResponseServerError(
            render_to_string('core/500.html', request=request)
        )
    
    def _check_connection(self):
        """Check if the PostgreSQL database connection is still viable"""
        try:
            with connection.cursor() as cursor:
                # Test the connection with a simple query
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result and result[0] == 1
        except Exception as e:
            logger.warning(f"Database connection check failed: {str(e)}")
            return False
    
    def _find_slow_queries(self, queries, threshold):
        """Find slow queries exceeding the threshold (in seconds)"""
        slow_queries = []
        for query in queries:
            try:
                query_time = float(query.get('time', 0))
                if query_time > threshold:
                    slow_queries.append({
                        'sql': query.get('sql', ''),
                        'time': query_time
                    })
            except (ValueError, TypeError):
                pass
        
        # Sort by time (slowest first)
        slow_queries.sort(key=lambda q: q['time'], reverse=True)
        return slow_queries

class TimeoutMiddleware:
    """
    Middleware to prevent requests from hanging indefinitely
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout = getattr(settings, 'REQUEST_TIMEOUT', 30)  # Default 30 seconds
        # Longer timeout for AI-related routes
        self.ai_timeout = getattr(settings, 'AI_REQUEST_TIMEOUT', 55)  # Just under Gunicorn's 60s timeout

    def __call__(self, request):
        # Determine the appropriate timeout based on the path
        is_ai_request = '/mentor/' in request.path or '/chat/' in request.path or '/generate/' in request.path
        current_timeout = self.ai_timeout if is_ai_request else self.timeout
        
        timeout_flag = {'timed_out': False}
        result = {'response': None}
        
        def target():
            try:
                result['response'] = self.get_response(request)
            except Exception as e:
                if not timeout_flag['timed_out']:
                    # Only log if it wasn't a timeout
                    logger.error(f"Error in request: {str(e)}")
                    result['exception'] = e
                    
            # Force garbage collection to help with memory usage
            import gc
            gc.collect()
        
        # Start processing in a thread
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(current_timeout)
        
        if thread.is_alive():
            # Request is taking too long
            timeout_flag['timed_out'] = True
            logger.warning(f"Request timed out: {request.path} after {current_timeout} seconds")
            
            # Use our custom 408 template
            return HttpResponseRequestTimeout(
                render_to_string('core/408.html', {'request': request})
            )
        
        if 'exception' in result:
            raise result['exception']
            
        return result['response']

class RateLimitMiddleware:
    """
    Middleware to implement rate limiting
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limits = {
            'default': {'requests': 500, 'window': 60},  # 500 requests per minute (increased from 100)
            'api': {'requests': 200, 'window': 60},      # 200 API requests per minute (increased from 50)
            'login': {'requests': 10, 'window': 60},     # 10 login attempts per minute (increased from 5)
        }
        
        # Paths that should have stricter rate limiting
        self.api_paths = ['/api/', '/mentor/']
        self.login_paths = ['/login/', '/register/']

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def __call__(self, request):
        # Skip rate limiting for static and media files
        if '/static/' in request.path or '/media/' in request.path:
            return self.get_response(request)
            
        # Get client IP
        client_ip = self.get_client_ip(request)
        
        # Determine the rate limit category
        category = 'default'
        if any(request.path.startswith(path) for path in self.api_paths):
            category = 'api'
        elif any(request.path.startswith(path) for path in self.login_paths):
            category = 'login'
        
        # Get rate limit settings
        limit = self.rate_limits[category]
        
        # Create cache key
        cache_key = f"rate_limit:{category}:{client_ip}"
        
        # Get current request count
        request_count = cache.get(cache_key, 0)
        
        # Check if rate limit exceeded
        if request_count >= limit['requests']:
            logger.warning(f"Rate limit exceeded for {client_ip} in category {category}")
            return HttpResponseTooManyRequests(
                render_to_string('core/429.html', {'request': request})
            )
        
        # Increment request count
        cache.set(cache_key, request_count + 1, limit['window'])
        
        # Process the request
        response = self.get_response(request)
        
        # Add rate limit headers
        response['X-RateLimit-Limit'] = str(limit['requests'])
        response['X-RateLimit-Remaining'] = str(limit['requests'] - request_count - 1)
        response['X-RateLimit-Reset'] = str(int(time.time()) + limit['window'])
        
        return response

class UserActivityMiddleware:
    """
    Middleware to track user activity and update last seen
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.tracked_urls = [
            '/dashboard/',
            '/personality-test/',
            '/scenarios/',
            '/mentor/',
            '/community/',
            '/profile/',
            '/progress/',
        ]

    def __call__(self, request):
        response = self.get_response(request)
        
        # Only track authenticated users
        if request.user.is_authenticated:
            try:
                # Check if the URL should be tracked
                if any(request.path.startswith(url) for url in self.tracked_urls):
                    # Update last activity timestamp
                    if hasattr(request.user, 'profile'):
                        try:
                            profile = request.user.profile
                            profile.last_activity = timezone.now()
                            profile.save(update_fields=['last_activity'])
                        except Exception as e:
                            # Don't crash if profile update fails
                            logger.error(f"Error updating user profile activity: {str(e)}")
                    
                    # Log activity for certain pages
                    if hasattr(request.user, 'profile'):
                        try:
                            from core.models import UserActivity
                            
                            # Determine activity type based on URL
                            activity_type = 'page_view'
                            if 'scenarios' in request.path and 'result' in request.path:
                                activity_type = 'scenario'
                            elif 'personality-test/result' in request.path:
                                activity_type = 'assessment'
                                
                            # Log the activity
                            UserActivity.log_activity(request.user, activity_type)
                        except Exception as e:
                            logger.error(f"Error logging user activity: {str(e)}")
            except Exception as e:
                # Never let activity tracking crash the site
                logger.error(f"Error in UserActivityMiddleware: {str(e)}")
        
        return response 

class WorkerTimeoutMiddleware:
    """
    Middleware that monitors request processing time and memory usage
    to prevent worker timeouts and out-of-memory situations
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Initialize concurrent request tracking
        self._concurrent_ai_requests = 0
        self._lock = threading.Lock()
        
        # Default settings if not defined in Django settings
        self.time_limit = getattr(settings, 'WORKER_TIME_LIMIT', 50)  # 50 seconds
        self.memory_limit_mb = getattr(settings, 'WORKER_MEMORY_LIMIT_MB', 450)  # 450 MB
        self.max_concurrent_ai_requests = getattr(settings, 'MAX_CONCURRENT_AI_REQUESTS', 3)
    
    def __call__(self, request):
        # Skip monitoring for static files or admin requests
        if request.path.startswith('/static/') or request.path.startswith('/admin/'):
            return self.get_response(request)
            
        # Check memory usage before processing
        process = psutil.Process(os.getpid())
        start_memory = process.memory_info().rss / 1024 / 1024
        if start_memory > self.memory_limit_mb:
            logger.warning(f"High memory usage before request: {start_memory:.2f}MB")
            return JsonResponse({
                'error': 'Server is currently under high load. Please try again in a moment.'
            }, status=503)
        
        # Record start time
        start_time = time.time()
        
        # Check if this is a resource-intensive endpoint
        is_resource_intensive = any([
            '/api/chat/' in request.path,
            '/community/' in request.path,
            '/generate/' in request.path,
            '/openai/' in request.path
        ])
        
        # For AI-intensive requests, check concurrent limit
        if is_resource_intensive and '/openai/' in request.path:
            with self._lock:
                if self._concurrent_ai_requests >= self.max_concurrent_ai_requests:
                    logger.warning(f"Too many concurrent AI requests ({self._concurrent_ai_requests})")
                    return JsonResponse({
                        'error': 'Too many AI requests in progress. Please try again shortly.'
                    }, status=503)
                self._concurrent_ai_requests += 1
        
        try:
            # Process the request
            response = self.get_response(request)
            
            # Post-processing checks
            elapsed = time.time() - start_time
            end_memory = process.memory_info().rss / 1024 / 1024
            memory_delta = end_memory - start_memory
            
            # Log high-risk requests for monitoring
            if elapsed > (self.time_limit / 2) or memory_delta > 50:
                logger.warning(
                    f"High-risk request completed: {request.path} - "
                    f"Time: {elapsed:.2f}s, Memory delta: {memory_delta:.2f}MB"
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Request error: {request.path} - {str(e)}")
            raise
            
        finally:
            # Always decrement AI request counter if needed
            if is_resource_intensive and '/openai/' in request.path:
                with self._lock:
                    self._concurrent_ai_requests -= 1

class SocialAuthExceptionMiddleware(MiddlewareMixin):
    """Middleware that handles Social Auth AuthExceptions."""
    def process_exception(self, request, exception):
        if isinstance(exception, AuthException):
            # Extract details for logging
            message = str(exception)
            backend_name = getattr(exception, 'backend', 'unknown')
            if hasattr(backend_name, 'name'):
                backend_name = backend_name.name
            
            # Log the exception details with more context
            logger.warning(f"Social auth exception caught by middleware: {message} (Backend: {backend_name})")
            logger.warning(f"Request path: {request.path}")
            logger.warning(f"Exception details: {repr(exception)}")
            
            # Get more details about the current state
            if hasattr(exception, 'response'):
                response = getattr(exception, 'response', {})
                if response:
                    try:
                        logger.warning(f"Response data: {response}")
                    except:
                        pass
            
            # Only store in session, don't add to messages here
            # The social_auth_error view will handle adding to messages
            request.session['social_auth_error'] = {
                'message': message,
                'backend': backend_name,
                'details': repr(exception),
            }
            
            # Redirect to dedicated error handler
            return redirect('core:social_auth_error')
        return None

# New middleware class to handle timeouts for long-running requests
class TimeoutMiddleware:
    """Middleware to handle timeouts for long-running requests."""
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Start a timer
        start_time = time.time()
        
        # Process the request
        response = self.get_response(request)
        
        # Check the elapsed time
        elapsed_time = time.time() - start_time
        if elapsed_time > 30:  # Log a warning if request takes more than 30 seconds
            logger.warning(f"Long-running request detected: {request.path} - {elapsed_time:.2f}s")
            
        return response

# New middleware class to check worker memory usage and prevent excessive consumption
class WorkerTimeoutMiddleware:
    """Middleware to check worker memory usage and prevent excessive consumption."""
    def __init__(self, get_response):
        self.get_response = get_response
        self.process = psutil.Process(os.getpid())
        
    def __call__(self, request):
        # Check memory usage
        memory_use = self.process.memory_info().rss / 1024 / 1024  # Convert to MB
        if memory_use > 450:  # 450 MB threshold
            logger.critical(f"Worker memory usage critical: {memory_use:.2f} MB")
            # Handle the memory issue - log only in this case
            
        return self.get_response(request)

class SocialAuthBackendFixMiddleware(MiddlewareMixin):
    """Middleware to ensure social auth backends are properly registered."""
    
    def process_request(self, request):
        """Ensure OAuth backends are registered before each request."""
        if not SOCIAL_AUTH_IMPORTS_AVAILABLE:
            return None
            
        # Check if request path is related to social auth
        if request.path.startswith('/social-auth/'):
            # Ensure Google OAuth2 backend is registered
            if 'google-oauth2' not in BACKENDSCACHE:
                logger.warning("GoogleOAuth2 backend not found in BACKENDSCACHE, registering it manually")
                BACKENDSCACHE['google-oauth2'] = GoogleOAuth2
            
            # Ensure Github OAuth2 backend is registered
            if 'github' not in BACKENDSCACHE:
                from social_core.backends.github import GithubOAuth2
                logger.warning("GithubOAuth2 backend not found in BACKENDSCACHE, registering it manually")
                BACKENDSCACHE['github'] = GithubOAuth2
                
            # Log all registered backends for debugging
            logger.info(f"Registered backends after fix: {list(BACKENDSCACHE.keys())}")
                
        return None 