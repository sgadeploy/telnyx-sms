from celery import Celery
from dotenv import load_dotenv
import os

load_dotenv()
REDIS_URL = os.getenv("REDIS_URL")

celery = Celery('tasks', broker=REDIS_URL)

@celery.task
def send_bulk_sms(numbers, message):
    from app.routes import send_sms
    for number in numbers:
        send_sms(number, message)