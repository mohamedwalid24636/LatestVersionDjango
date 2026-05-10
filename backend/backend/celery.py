import os
from celery import Celery

# ==============================================================================
# DJANGO SETTINGS MODULE
# ==============================================================================

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# ==============================================================================
# CREATE CELERY APP
# ==============================================================================

app = Celery('backend')

# ==============================================================================
# LOAD CONFIG FROM DJANGO SETTINGS
# ==============================================================================

app.config_from_object('django.conf:settings', namespace='CELERY')

# ==============================================================================
# AUTO DISCOVER TASKS
# ==============================================================================

app.autodiscover_tasks()

# ==============================================================================
# GLOBAL CELERY CONFIG (PRODUCTION SAFE)
# ==============================================================================

app.conf.update(
    timezone='Africa/Cairo',
    enable_utc=True,

    # تحسين الأداء والاستقرار
    task_track_started=True,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',

    # منع ضغط زائد على السيرفر
    worker_prefetch_multiplier=1,

    # إعادة المحاولة الذكية
    task_acks_late=True,
)

# ==============================================================================
# DEBUG TASK (SAFE TEST ONLY)
# ==============================================================================

@app.task(bind=True)
def debug_task(self):
    print(f"[CELERY DEBUG TASK] Request: {self.request!r}")