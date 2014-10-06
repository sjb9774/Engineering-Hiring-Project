import os

SECRET_KEY = "ITS_A_SECRET_TO_EVERYBODY"
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.abspath("accounting.sqlite")
