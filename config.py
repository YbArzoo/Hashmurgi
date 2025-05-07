import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'sX!7uR#eP9@zLmT8^c3Gb$NqWx&V5jYp')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///hashmurgi.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join('static', 'uploads')
