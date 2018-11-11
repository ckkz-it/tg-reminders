import os
import datetime
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reminders.settings')

app = Celery('reminders', broker=settings.BROKER_URL, include=['core.tasks'])
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.beat_schedule = {
    'check_reminders': {
        'task': 'CheckReminders',
        'schedule': datetime.timedelta(minutes=1)
    }
}
