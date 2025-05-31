"""
Custom pipeline functions for python-social-auth
"""
from .utils import handle_user_registered
import logging
import json
from django.conf import settings

logger = logging.getLogger(__name__)

def debug_social_auth(strategy, backend, *args, **kwargs):
    """
    Debug function to log social auth details
    """
    logger.info(f"Social auth debug: Backend={backend.name if backend else 'None'}")
    logger.info(f"Social auth debug: Available backends={list(settings.AUTHENTICATION_BACKENDS)}")
    
    # Log response data (careful with sensitive data)
    response = kwargs.get('response', {})
    if response:
        safe_response = {k: v for k, v in response.items() 
                        if k not in ('access_token', 'id_token', 'refresh_token')}
        logger.info(f"Social auth response: {json.dumps(safe_response)}")
    
    # Check for any errors
    if 'error' in kwargs:
        logger.error(f"Social auth error: {kwargs.get('error')}")
    
    return None  # Continue the pipeline

def send_welcome_notification(strategy, details, user=None, is_new=False, *args, **kwargs):
    """
    Send a welcome notification to new users who sign up via social auth
    """
    logger.info(f"Social auth pipeline called for {user.email if user else 'unknown'}, is_new={is_new}")
    
    if user and is_new:
        handle_user_registered(user, is_new=True)
    
    return {
        'user': user,
        'is_new': is_new,
    } 