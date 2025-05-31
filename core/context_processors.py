from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def global_settings(request):
    """
    Add common data to all templates
    """
    return {
        'DEBUG': settings.DEBUG,
        'SITE_NAME': 'Desiq',
        'SITE_VERSION': '1.0.0',
    }

def user_data(request):
    """
    Add user-specific data to all templates
    """
    context = {
        'is_authenticated': request.user.is_authenticated,
        'is_premium': False,
        'user_level': 0,
    }
    
    if not request.user.is_authenticated:
        return context
        
    try:
        # Ensure database connection is viable before accessing profile
        from django.db import connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception as e:
            logger.error(f"Database connection error in context processor: {str(e)}")
            # Return basic context without profile data if DB is not available
            return context
            
        # Get profile safely with proper error handling
        profile = getattr(request.user, 'profile', None)
        if profile is not None:
            context.update({
                'user_profile': profile,
                'is_premium': profile.is_premium,
                'user_level': profile.level,
            })
        else:
            # Handle case where user has no profile
            logger.warning(f"User {request.user.username} has no profile")
            context.update({
                'user_profile': None,
                'is_premium': False,
                'user_level': 0,
            })
    except Exception as e:
        # Log the error but continue without failing
        logger.error(f"Error getting user profile: {str(e)}")
        context.update({
            'user_profile': None,
        })
    
    return context 