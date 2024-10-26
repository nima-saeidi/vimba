import os


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('postgresql://postgres:n1m010@localhost:5432/vimba')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')

config = Config()
