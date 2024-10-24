import os
import bcrypt
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from web_blog import Post, Comment, PostTags, Role, Tag, User

# Create a flask app
app = Flask(__name__)
app.secret_key = os.urandom(24) #Temporary generation of key on run.
                            #Turn into environment variable for release

# Setup flask SQLAlchemy
# Database is named blog.db and located in this same directory
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
# Save some overhead
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

USERNAME = 'admin'
HASHED_PASSWORD = '$2b$12$9GjnwibqITthzmS333Q/HOcDX/fn7YSuS8x7tyCjZ50KZlgFhQ1Tq'
ROLE = 1

def selectUsers(mode):
    if mode == 'dev':
        add_admin()
        return True
    elif mode == 'live':
        remove_admin()
        return True
    else:
        return False

def add_admin():
    admin_access = User(username=USERNAME, password_hash=HASHED_PASSWORD, role_id=ROLE)

    with app.app_context():
        db.session.add(admin_access)
        db.session.commit()

def remove_admin():
    with app.app_context():
        admin_access = db.session.scalar(
            db.select(User).filter_by(username=USERNAME).limit(1)
        )
        db.session.delete(admin_access)
        db.session.commit()

if __name__ == "__main__":

    ###For development only remove for production
    with app.app_context():
        db.create_all()
    ###
    EXIT_LOOP = False

    while not EXIT_LOOP:
        EXIT_LOOP = selectUsers(input("Enter mode: "))
