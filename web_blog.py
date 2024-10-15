import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, abort, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user

# Create a flask app
app = Flask(__name__)
app.secret_key = os.urandom(24) #Temporary generation of key on run.
                            #Turn into environment variable for release

# Setup flask SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db' # Database is named blog.db and located in this same directory
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Save some overhead

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

### Processing
@login_manager.user_loader
def load_user(user_id):
    return users.get('admin') if user_id == '1' else None

# Post class inheriting from db.Model inside of Flask
class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Useful for debugging
    def __repr__(self):
        return f'<Post {self.title}>'

# User Loader
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
    # Query all posts from the database
    posts = Post.query.all()  # Fetch all posts

    return render_template('base.html', posts=posts)

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

@app.route('/view_post/<int:post_id>')
def view_post(post_id):
    post = db.session.get(Post, post_id)
    if post is None:
        abort(404)
    return render_template('view_post.html', post=post)


### Private Routing

@app.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        post_title = request.form['title']
        post_content = request.form['content']
        date_string = request.form['date']

        # Edit content to preserve formatting using html
        post_content = post_content.replace('\n', '<br>') # Replace new lines

        # Convert the date string to a python date object
        post_date = datetime.strptime(date_string, '%Y-%m-%d').date()

        new_post = Post(title=post_title, content=post_content, date=post_date)

        db.session.add(new_post)
        db.session.commit()
        flash('Post created successfully!')

        return redirect(url_for('home')) #return to the home page

    today_date = datetime.today().strftime('%Y-%m-%d')  # Get today's date in YYYY-MM-DD format
    return render_template('create_post.html', today_date=today_date)

@app.route('/debug_posts')
@login_required
def debug_posts():
    # Query all posts from the database
    posts = Post.query.all()  # Fetch all posts

    # Render a simple template to display the posts
    return render_template('debug_posts.html', posts=posts)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == "__main__":

    ###TODO: For development only remove for production
    with app.app_context():
        db.create_all()
    ###

    app.run(debug=True, port=5000)
