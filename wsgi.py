"""Production WSGI entry point. Run with: gunicorn wsgi:app"""
from app import create_app

app = create_app()
