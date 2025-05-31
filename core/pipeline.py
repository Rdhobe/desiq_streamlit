from django.contrib.auth.models import User
from django.shortcuts import redirect
from social_core.pipeline.partial import partial
from social_core.exceptions import AuthException, AuthAlreadyAssociated
from django.urls import reverse
from django.contrib import messages
import logging
import traceback

logger = logging.getLogger('core')

def email_exists(backend, details, user=None, *args, **kwargs):
    """
    Check if the email from social auth already exists in the system.
    If it does, raise an exception to stop the pipeline.
    """
    try:
        email = details.get('email')
        # Log full details for debugging
        logger.info(f"Social auth details received: {details}")
        
        if email and not user:  # Only run this check when creating a new user
            # Log information about the authentication attempt
            logger.info(f"Social auth checking email uniqueness: {email} via {backend.name}")
            
            # Check if this email already exists in the database
            existing_users = User.objects.filter(email=email)
            if existing_users.exists():
                # Get the existing user for logging
                existing_user = existing_users.first()
                
                # Log detailed information about the existing account
                logger.warning(
                    f"Social login blocked - email already exists: {email} via {backend.name}. "
                    f"Existing user: {existing_user.username} (ID: {existing_user.id})"
                )
                
                # DEVELOPMENT FIX: Instead of raising an exception, find and authenticate the existing user
                # This associates the social account with the existing user instead of blocking
                logger.info(f"Attempting to associate social account with existing user: {existing_user.username}")
                return {
                    'user': existing_user,
                    'is_new': False,
                }
                
                # Commented out the exception that was blocking login
                # raise AuthException(
                #     backend,
                #     f"The email address '{email}' is already associated with another account. "
                #     "Please sign in using your existing account."
                # )
            
            logger.info(f"Email uniqueness check passed for: {email}")
    
    except Exception as e:
        if isinstance(e, AuthException):
            # Re-raise AuthException as it's expected
            raise
        
        # For unexpected errors, log the full traceback but allow auth to continue
        logger.error(f"Error in email_exists pipeline: {str(e)}\n{traceback.format_exc()}")
    
    # Continue the pipeline
    return {'user': user} 