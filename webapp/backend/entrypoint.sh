#!/bin/sh
set -e

echo "⏳ Waiting for database to be ready..."
# Already guaranteed by healthcheck in docker-compose, but be safe
python -c "
import sys, time, os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db import connection
for i in range(30):
    try:
        connection.ensure_connection()
        print('✅ Database ready.')
        sys.exit(0)
    except Exception as e:
        print(f'   ({i+1}/30) Not ready yet: {e}')
        time.sleep(1)
print('❌ Database not available after 30 seconds.')
sys.exit(1)
"

echo "📦 Running migrations..."
python manage.py migrate --no-input

echo "🔍 Scanning MIDI files..."
python manage.py scan_midis || echo "   (scan skipped — media dirs may be empty)"

echo "👤 Creating superuser if needed..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
import os
User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(
        username=username,
        email=os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com'),
        password=os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin'),
    )
    print(f'✅ Superuser created: {username}')
else:
    print(f'ℹ️  Superuser already exists: {username}')
"

exec "$@"
