from celery import Celery
from backend.config import config as app_config # Import the application's config instance

# Use the configuration from app_config
# These should be set in your environment or .env file for production
# For the sandbox, they will default to the redis URL defined in config.py
BROKER_URL = app_config.CELERY_BROKER_URL
RESULT_BACKEND = app_config.CELERY_RESULT_BACKEND

# Initialize Celery
# The first argument is the traditional name of the current module.
# It's used for auto-generating task names.
celery_app = Celery('backend.celery_app',
                    broker=BROKER_URL,
                    backend=RESULT_BACKEND,
                    include=['backend.celery_app']) # Add module itself to include list for tasks

# Optional: Update Celery configuration with other settings from app_config if needed
# celery_app.conf.update(
#     task_serializer='json',
#     accept_content=['json'],  # Ignore other content
#     result_serializer='json',
#     timezone='UTC',
#     enable_utc=True,
# )

# Optional Flask integration (conceptual for now, as Flask app structure might vary)
# This ensures tasks run within the Flask application context,
# allowing access to Flask extensions, database connections, etc.
#
# from flask import current_app # Or your Flask app instance
#
# class ContextTask(celery_app.Task):
#     def __call__(self, *args, **kwargs):
#         # Assuming you have a way to get or create your Flask app instance
#         # For example, if you have a create_app() factory:
#         # from backend.main import create_app # Adjust import path as needed
#         # flask_app = create_app()
#         # with flask_app.app_context():
#         #     return self.run(*args, **kwargs)
#         #
#         # If running standalone or prefer not to tie directly to create_app in this file:
#         # This basic version won't have Flask app context.
#         # For tasks needing app context (e.g. DB access), further setup is required.
#         print(f"Executing task {self.name} with args {args} and kwargs {kwargs}")
#         return self.run(*args, **kwargs)

# celery_app.Task = ContextTask


@celery_app.task
def example_task(x, y):
    """A simple example task that adds two numbers."""
    result = x + y
    print(f"Task example_task: {x} + {y} = {result}")
    return result

if __name__ == '__main__':
    # This allows running the Celery worker directly using:
    # python -m backend.celery_app worker -l info
    # (Though typically you'd use the `celery` CLI command)
    celery_app.start()
