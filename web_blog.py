from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
import sys

# Add the parent directory to the system path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

app = Flask(__name__)
app.secret_key = os.urandom(24) #Temporary generation of key on run.
                                #Turn into environment variable for release

# Setup flask-login
login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

# User storage (Just for me, for now)
users = {
    'admin': User(1, 'admin', 'password') #TODO update for production, this is fine for publishing
}

### Public Routing

@app.route('/')
def home():
    return render_template('base.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.get(username)

        if user and user.password == password:
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials. Please try again')

    return render_template('login.html')


### Private Routing

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

### Processing

@login_manager.user_loader
def load_user(user_id):
    return users.get('admin') if user_id == '1' else None

if __name__ == "__main__":
    app.run(debug=True, port=5000)
