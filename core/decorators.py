from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.contrib import messages
from django.shortcuts import redirect

def user_passes_test_with_403(test_func):
    """
    Decorator for views that checks that the user passes the given test,
    redirecting to a custom 403 page if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            return render(request, 'core/403.html', status=403)
        return _wrapped_view
    return decorator

def premium_required(view_func):
    """
    Decorator for views that checks if the user has a premium account,
    redirecting to the upgrade page if necessary.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.profile.is_premium:
            return view_func(request, *args, **kwargs)
        messages.warning(request, "This feature requires a premium account.")
        return redirect('core:upgrade_subscription')
    return _wrapped_view

def staff_member_required_with_403(view_func):
    """
    Decorator for views that checks if the user is a staff member,
    redirecting to a custom 403 page if necessary.
    """
    def check_if_staff(user):
        return user.is_staff
    return user_passes_test_with_403(check_if_staff)(view_func) 