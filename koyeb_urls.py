"""
Custom URL configuration for Koyeb deployment.
This file is used to insert our debug views before the main URL patterns.
"""

from django.urls import path, include
from debug_view import debug_info
from django.http import HttpResponse

# Simple health check view
def health_check(request):
    return HttpResponse("OK")

# Simple non-redirecting index view
def index_view(request):
    return HttpResponse("""
        <html>
            <head><title>DesiQ Debug Page</title></head>
            <body>
                <h1>DesiQ Debug Page</h1>
                <p>This is a debug page for the DesiQ application.</p>
                <p>If you can see this, the server is working but there may be issues with the main application.</p>
                <p><a href="/debug/">View Debug Information</a></p>
                <p><a href="/health/">Health Check</a></p>
                <p><a href="/admin/">Admin</a></p>
            </body>
        </html>
    """)

# Override URL patterns to include debug views
urlpatterns = [
    # Debug views
    path('', index_view),  # Non-redirecting index page
    path('debug/', debug_info),
    path('health/', health_check),
    
    # Include the main URL patterns from the project
    path('app/', include('desiq.urls')),
] 