release: python manage.py migrate --verbosity=2
web: python manage.py migrate --verbosity=2 && gunicorn OrionWorkSec.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120
web: chmod +x start.sh && ./start.sh