FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_VERSION=4.2.11
ENV DJANGO_SETTINGS_MODULE=koyeb_settings

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install gunicorn && \
    pip uninstall -y django || echo "Django not previously installed" && \
    pip install Django==${DJANGO_VERSION} --no-cache-dir && \
    pip install -r requirements.txt --no-cache-dir

# Copy project
COPY . .

# Create necessary directories
RUN mkdir -p staticfiles/css staticfiles/js staticfiles/img media logs

# Collect static files
RUN python manage.py collectstatic --no-input --clear

# Fix admin static files
RUN python fix_admin_static.py

# Set permissions
RUN chmod -R 755 staticfiles static

# Expose port
EXPOSE 8000

# Create entrypoint script to run migrations before starting
RUN echo '#!/bin/bash\necho "Running health check..."\npython health_check.py\necho "Running migrations..."\npython manage.py migrate --no-input\necho "Starting gunicorn..."\nexec gunicorn koyeb_wsgi:application -c gunicorn_config.py' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Use entrypoint script
CMD ["/app/entrypoint.sh"] 