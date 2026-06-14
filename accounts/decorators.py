from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect


def role_required(role):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'Please login to continue.')
                return redirect('home')
            if request.user.role != role:
                messages.error(request, 'You are not allowed to access that page.')
                if request.user.role == 'ADMIN':
                    return redirect('admin_dashboard')
                return redirect('distributor_dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
