"""Email and in-app notifications.

Every send is a Celery task. Nothing in a request/response cycle waits on SMTP.
"""
