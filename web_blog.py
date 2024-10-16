import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, abort, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

# Create a flask app
app = Flask(__name__)
app.secret_key = os.urandom(24) #Temporary generation of key on run.
                            #Turn into environment variable for release

# Setup flask SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db' # Database is named blog.db and located in this same directory
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Save some overhead

db = SQLAlchemy(app)

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

# Many to many table to bridge posts and tags
class PostTags(db.Model):
    __tablename__ = 'post_tags'
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'), primary_key=True)

# Role model
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)

    def __repr__(self):
        return f'<Role {self.name}>'
    
# Tag model
class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    # Relationship to link tags to posts
    posts = db.relationship('Post', secondary='post_tags', backref='tags')

    def __repr__(self):
        return f'<Tag {self.name}>'

# User Loader
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id')) # Link to the Role table

    role = db.relationship('Role', backref='users') # Releationship to Role

    def __repr__(self):
        return f'<User {self.username}>'
 
    @property
    def is_admin(self):
        return self.role.name == 'admin'

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)

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
        user = db.session.scalars(
                db.select(User).filter_by(username=username).limit(1)
            ).first()

        if user and user.password_hash == password:
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

@app.route('/delete_post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    post = db.session.get(Post, post_id)
    if post is None:
        abort(404)
    
    if current_user.is_admin:
        db.session.delete(post)
        db.session.commit()
        flash('Post deleted successfully!', 'success')
        return redirect(url_for('home'))
    else:
        flash('You do not have permission to delete this post.', 'danger')

@app.route('/manage_tags')
@login_required
def manage_tags():
    if not current_user.is_admin:
        flash('You do not have permission to manage tags.', 'danger')
        return redirect(url_for('home'), 401)
    
    with app.app_context():
            tags = db.session.execute(
                            db.select(Tag)
                        ).scalars().all()
            
    return render_template('manage_tags.html', tags=tags), 200
    
@app.route('/delete_tag/<int:tag_id>', methods=['POST'])
@login_required
def delete_tag(tag_id):
    if not current_user.is_admin:
        flash('You do not have permission to delete tags.', 'danger')
        return redirect(url_for('home'), 401)
    
    with app.app_context():
        tag = db.session.get(Tag, tag_id)
        if tag:
            db.session.delete(tag)
            db.session.commit()
            flash('Tag deleted sucessfully!', 'success')
            with app.app_context():
                tags = db.session.execute(
                                db.select(Tag)
                            ).scalars().all()
            return render_template('manage_tags.html', tags=tags), 204
        flash('Tag not found', 'danger')
        with app.app_context():
            tags = db.session.execute(
                            db.select(Tag)
                        ).scalars().all()
        return render_template('manage_tags.html', tags=tags), 404

@app.route('/create_tag', methods=['POST'])
@login_required
def create_tag():
    if not current_user.is_admin:
        flash('You do not have permission to create tags.', 'danger')
        return redirect(url_for('home'), 401)
    
    if request.method == 'POST':

        tag_name = request.form['tag_name']

        with app.app_context():
            tag = db.session.scalars(
                    db.select(Tag).filter_by(name=tag_name).limit(1)
                ).first()
            if tag:
                flash('Tag already exists.', 'danger')
            else:
                new_tag = Tag(name=tag_name)
                db.session.add(new_tag)
                db.session.commit()
                flash('Tag created successfully!', 'success')

        with app.app_context():
            tags = db.session.execute(
                            db.select(Tag)
                        ).scalars().all()
            
        return render_template('manage_tags.html', tags=tags), 201

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
