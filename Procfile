release: python manage.py migrate --verbosity=2
web: gunicorn OrionWorkSec.wsgi:application --bind 0.0.0.0:$PORT