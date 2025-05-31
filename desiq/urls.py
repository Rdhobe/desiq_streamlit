"""
URL configuration for desiq project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from core.health import health_check
from core.admin_views import admin_login

urlpatterns = [
    # Override the admin login URL
    path('admin/login/', admin_login, name='admin_login'),
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('health/', health_check, name='health_check'),  # Root-level health check for Render
    path('social-auth/', include('social_django.urls', namespace='social')),  # Social authentication URLs
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Add staticfiles_urlpatterns for development and production
urlpatterns += staticfiles_urlpatterns()

# Error handlers
handler404 = 'core.views.handler404'
handler500 = 'core.views.handler500'
handler403 = 'core.views.handler403'
handler400 = 'core.views.handler400'
handler408 = 'core.views.handler408'
