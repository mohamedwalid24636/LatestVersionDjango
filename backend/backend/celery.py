import os
from celery import Celery

# ==============================
# Django settings module
# ==============================
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# ==============================
# Create Celery app
# ==============================
app = Celery('backend')

# ==============================
# Load settings from Django
# ==============================
app.config_from_object('django.conf:settings', namespace='CELERY')

# ==============================
# Auto discover tasks
# ==============================
app.autodiscover_tasks()

# ==============================
# Optional production config
# ==============================
app.conf.update(
    timezone='Africa/Cairo',
    enable_utc=True,
)

# ==============================
# Debug task (for testing only)
# ==============================
@app.task(bind=True)
def debug_task(self):
    print(f"[CELERY DEBUG TASK] Request: {self.request!r}")