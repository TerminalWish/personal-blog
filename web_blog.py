import os
from datetime import datetime
from flask import Flask, jsonify, render_template, redirect, url_for, flash, abort, request
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

    # Link to comments for easy access
    comments = db.relationship('Comment', cascade='all, delete', backref='post')

    # Useful for debugging
    def __repr__(self):
        return f'<Post {self.title}>'
    
# Comment model
class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id', ondelete="CASCADE"))
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Useful for debugging
    def __repr__(self):
        return f'<Comment {self.title}>'

# Many to many table to bridge posts and tags
class PostTags(db.Model):
    __tablename__ = 'post_tags'
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'), primary_key=True)

    # Useful for debugging
    def __repr__(self):
        return f'<PostTags {self.post_id}, {self.tag_id}>'

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
    posts = Post.query.order_by(Post.date.desc()).all() # Fetch all posts ordered by newest date

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

    # Fetch associated tags
    with app.app_context():
        post_tags = db.session.execute(
            db.select(PostTags).filter_by(post_id=post.id)
        ).scalars().all()

    # Get the tag ids
    tag_ids = [tag.tag_id for tag in post_tags]


    # Get tag names
    tags = []
    with app.app_context():
        for tag in tag_ids:
            tag_name = db.session.execute(
                db.select(Tag).filter_by(id=tag)
            ).scalar_one()
            tags.append(tag_name)

    return render_template('view_post.html', post=post, tags=tags)

@app.route('/fetch_tags', methods=['GET'])
def fetch_tags():
    
    with app.app_context():
            tags = db.session.execute(
                            db.select(Tag)
                        ).scalars().all()
    
    tags_list = [{'id': tag.id, 'name': tag.name} for tag in tags]

    return jsonify({'tags': tags_list})

@app.route('/fetch_posts_by_tags', methods=['GET'])
def fetch_posts_by_tags():
    # Get the tag IDs from the query string
    tag_ids = request.args.get('ids', '')  # Get the 'ids' parameter from the URL
    if not tag_ids:
        return jsonify({'posts': []})  # Return an empty list if no IDs are provided

    # Split the comma-separated string into a list and convert to integers
    tag_ids = [int(tag) for tag in tag_ids.split(',') if tag]

    with app.app_context():
        posts = db.session.execute(
            db.select(Post).
            join(PostTags).
            where(PostTags.tag_id.in_(tag_ids)).  # Use IN to filter by multiple tag IDs
            order_by(Post.date.desc())
        ).scalars().all()

    unique_posts = {}
    for post in posts:
        if post.id not in unique_posts:
            unique_posts[post.id] = post

    post_list = [{'id': post.id, 'title': post.title, 'date': post.date} for post in unique_posts.values()]

    return jsonify({'posts': post_list})

@app.route('/fetch_all_posts', methods=['GET'])
def fetch_all_posts():
    posts = Post.query.order_by(Post.date.desc()).all() # Fetch all posts ordered by newest date

    post_list = [{'id': post.id, 'title': post.title, 'date': post.date} for post in posts]

    return jsonify({'posts': post_list})

@app.route('/add_comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    comment_title = request.form['title']
    comment_content = request.form['content']

    # Basic validation
    if not comment_title or not comment_content:
        flash('Title and content cannot be empty!', 'danger')
        return redirect(url_for('view_post', post_id=post_id))

    new_comment = Comment(title=comment_title, content=comment_content, post_id=post_id)

    db.session.add(new_comment)
    db.session.commit()

    return redirect(url_for('view_post', post_id=post_id))



### Private Routing

@app.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        post_title = request.form['title']
        post_content = request.form['content']
        date_string = request.form['date']
        
        # Retrieve the tags string and split it into a list
        selected_tags = request.form['tags'].split(',')  # Split the comma-separated string into a list

        # Filter for empty tags (such as when no tags are applied)
        selected_tags = [tag for tag in selected_tags if tag]

        # Edit content to preserve formatting using html
        post_content = post_content.replace('\n', '<br>') # Replace new lines

        # Convert the date string to a python date object
        post_date = datetime.strptime(date_string, '%Y-%m-%d').date()

        new_post = Post(title=post_title, content=post_content, date=post_date)

        db.session.add(new_post)
        db.session.commit()

        # Associate selected tags with the post
        for tag_id in selected_tags:
            post_tag = PostTags(post_id=new_post.id, tag_id=tag_id)
            db.session.add(post_tag)
            db.session.commit()

        flash('Post created successfully!')

        return redirect(url_for('home')) #return to the home page

    with app.app_context():
        all_tags = db.session.execute(
            db.select(Tag)
        ).scalars().all()

    today_date = datetime.today().strftime('%Y-%m-%d')  # Get today's date in YYYY-MM-DD format
    return render_template('create_post.html', today_date=today_date, all_tags=all_tags)

@app.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = db.session.get(Post, post_id)
    if post is None:
        abort(404)

    if request.method == 'POST':
        # Update the post attributes with new values from the form
        post.title = request.form['title']
        post.content = request.form['content']
        post.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()

        # Retrieve the tags string and split it into a list
        selected_tags = [int(tag) for tag in request.form['tags'].split(',') if tag.strip()]

        # Delete relationship entries
        with app.app_context():
            post_tags = db.session.execute(
                db.select(PostTags).
                filter_by(post_id=post.id)
            ).scalars().all()
        
        post_tag_tag_ids = []
        for post_tag in post_tags:
            post_tag_tag_ids.append(post_tag.tag_id)

        for post_tag in post_tags:
            if post_tag not in selected_tags:
                db.session.delete(post_tag)
            else:
                print("tried to remove?")
                selected_tags.remove(post_tag)
     
        # Associate selected tags with the post
        for tag_id in selected_tags:
            post_tag = PostTags(post_id=post_id, tag_id=tag_id)
            db.session.add(post_tag)

        # Commit the changes to the database
        db.session.commit()

        flash('Post updated successfully!', 'success')
        return redirect(url_for('view_post', post_id=post.id))  # Redirect to the updated post

    # If GET request, render the edit post form pre-filled with current post data
    with app.app_context():
        all_tags = db.session.execute(
            db.select(Tag)
        ).scalars().all()

    return render_template('edit_post.html', post=post, all_tags=all_tags)

@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = db.session.get(Comment, comment_id)
    if comment is None:
        abort(404)

    if not current_user.is_admin:
        flash('You do not have permission to delete this post.', 'danger')
        return redirect(url_for('home'), 401)
    
    # Save post id for redirect
    post_id = comment.post_id

    db.session.delete(comment)
    db.session.commit()

    return redirect(url_for('edit_post', post_id=post_id), 204)

@app.route('/delete_post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    post = db.session.get(Post, post_id)
    if post is None:
        abort(404)
    
    if not current_user.is_admin:
        flash('You do not have permission to delete this post.', 'danger')
        return redirect(url_for('home'), 401)
    
    # Delete post
    db.session.delete(post)
    db.session.commit()

    # This query retrieves all tags that have no associated entries in the PostTags table.
    # It uses an outer join to include all tags, even those that do not have a corresponding
    # post association, allowing us to identify orphaned tags (tags without posts).
    orphaned_tags = db.session.query(Tag).outerjoin(PostTags).filter(PostTags.post_id.is_(None)).all()

    for tag in orphaned_tags:
        db.session.delete(tag)

    db.session.commit()

    flash('Post deleted successfully!', 'success')
    return redirect(url_for('home'))
        

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
        #return Response(redirect(url_for('manage_tags')), status= 404)
        return render_template('manage_tags.html', tags=tags), 404

@app.route('/create_tag', methods=['POST'])
@login_required
def create_tag():
    if not current_user.is_admin:
        flash('You do not have permission to create tags.', 'danger')
        return redirect(url_for('home'), 401)
    
    if request.method == 'POST':

        if request.is_json:
            data = request.get_json()
            tag_name = data.get('tag_name')
        else:
            tag_name = request.form['tag_name']
        
        with app.app_context():
            tag = db.session.scalars(
                    db.select(Tag).filter_by(name=tag_name).limit(1)
                ).first()
            if tag:
                flash('Tag already exists.', 'danger')
                tags = db.session.execute(
                            db.select(Tag)
                        ).scalars().all()
                return render_template('manage_tags.html', tags=tags), 409
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
