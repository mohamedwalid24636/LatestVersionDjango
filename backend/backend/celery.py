import os
# from celery import Celery

# # set default Django settings module
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# # create celery app
# app = Celery('backend')

# # load config from Django settings
# app.config_from_object('django.conf:settings', namespace='CELERY')

# # auto-discover tasks from all installed apps
# app.autodiscover_tasks()

# # optional debug task
# @app.task(bind=True)
# def debug_task(self):
#     print(f"[CELERY DEBUG TASK] Request: {self.request!r}")import os
from celery import Celery

# ==============================
# Django settings module
# ==============================
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

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
# Optional: time settings safety
# ==============================
app.conf.update(
    timezone='Africa/Cairo',
    enable_utc=True,
)

# ==============================
# Debug task
# ==============================
@app.task(bind=True)
def debug_task(self):
    print(f"[CELERY DEBUG TASK] Request: {self.request!r}")

    