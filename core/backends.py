from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()

class EmailBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in using their email address.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Check if username contains @ to identify if it's an email
        if username and '@' in username:
            try:
                # Try to get a user by email
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                # No user found with this email
                return None
            except User.MultipleObjectsReturned:
                # Multiple users with same email, use the most recently created one
                user = User.objects.filter(email=username).order_by('-date_joined').first()
            
            # Check the password for the user found by email
            if user and user.check_password(password):
                return user
        
        # Fall back to the default behavior (username authentication)
        return super().authenticate(request, username, password, **kwargs) 