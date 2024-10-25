"""Web Blog python
   Written By: Geoff Armstrong

   Using Flask and SQLAlchemy the following code has produced the backend
   necessary for a personal blog. This blog is capable of housing posts,
   applying tags to highlight topics, and allow for users to leave comments on posts.

   This utilizes an SQLite database underneth to hold data entered via the front-end
   website that accompanies this program.

   Currently this program will only allow for users flagged in the database as having the
   admin role. No user registration is currently implemented so that means only those
   manually entered can hope to make and edit the information contained here in the back-end.
   As such, behavior for multiple admin users is not handled at any level.
"""

import os
from datetime import datetime
import bcrypt
from flask import Flask, jsonify, render_template, redirect, url_for, flash, abort, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin
from flask_login import login_user, login_required, logout_user, current_user
import plotly.express as px
import plotly.graph_objects as go

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

# Initialize Migrate
migrate = Migrate(app, db)

###
#   Please note: The following classes dealing with db.Model are
#   for constructing my database tables. As such they do not require
#   many methods, but SQLAlchemy wants what it wants. I've made the decision
#   to silence the "Too few public methods" pylint error for these classes
###

# Post class inheriting from db.Model inside of Flask
class Post(db.Model): # pylint: disable=R0903
    """Model for the Posts table.
       This table is responsible for holding the content of a post
       and to provide a location to attach Tags and Comments to.
       Deleting a Post row will remove any associated PostTag rows for any
       tag that is associated with the Post. If the Post is the last Post
       any particular Tag is associated with, the tag will also be deleted.
       Table has quick access to the comments table for easy populating of
       the comments section of a post view.
    """

    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.Date, nullable=False)
    view_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Link to comments for easy access
    comments = db.relationship('Comment', cascade='all, delete', backref='post')

    # Useful for debugging
    def __repr__(self):
        return f'<Post {self.title}>'

# Comment model
class Comment(db.Model): # pylint: disable=R0903
    """Model for the Comments table.
       Comments can be created by anyone that can view a Post (currently everyone)
       Comments are automatically removed when the Post they are attached to is deleted.
    """

    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(
              db.Integer,
              db.ForeignKey('posts.id', ondelete="CASCADE", name="fk_post_id_comments")
              )
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Useful for debugging
    def __repr__(self):
        return f'<Comment {self.title}>'

# Many to many table to bridge posts and tags
class PostTags(db.Model): # pylint: disable=R0903
    """Model for the PostTags table.
       Table is responsible for managing a many-to-many relationship
       between Posts and Tags. A row is removed any time either a Post or a
       Tag are removed.
       The existence of this table allows for easy lookup between the two tables
       particularlly from the tag to post side in order to populate lists of Posts
       that contain a tag.
    """

    __tablename__ = 'post_tags'
    post_id = db.Column(
              db.Integer,
              db.ForeignKey('posts.id', name="fk_post_id_posttags"),
              primary_key=True
              )
    tag_id = db.Column(
             db.Integer,
             db.ForeignKey('tags.id', name="fk_tag_id_posttags"),
             primary_key=True
             )

    # Useful for debugging
    def __repr__(self):
        return f'<PostTags {self.post_id}, {self.tag_id}>'

# Role model
class Role(db.Model): # pylint: disable=R0903
    """Model for the Role table.
       Role will provide permissions to users according to thier access level.
    """

    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)

    def __repr__(self):
        return f'<Role {self.name}>'

    __table_args__= (
        UniqueConstraint('name', name='uq_name_roles'),
    )

# Tag model
class Tag(db.Model): # pylint: disable=R0903
    """Model for the Tags table.
       Tags have an id and name and share a relationship with Posts
       via the PostTags table. Rows will be deleted when the last post
       they are associated with is deleted with the intention of keeping
       the tag list pruned of unrelated topics.
    """
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    view_count = db.Column(db.Integer, default=0)

    # Relationship to link tags to posts
    posts = db.relationship('Post', secondary='post_tags', backref='tags')

    def __repr__(self):
        return f'<Tag {self.name}>'

    __table_args__= (
        UniqueConstraint('name', name='uq_name_tags'),
    )

# Daily Stats Model
class DailyStats(db.Model): # pylint: disable=R0903
    """Model for the Daily Stats table.
       Daily stats are unique sets of data organized by dates.
       These are responsible for counting daily engagement metrics
       to watch site trafic inside the admin dashboard
    """
    __tablename__ = 'daily_stats'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    cumulative_views = db.Column(db.Integer, default=0) # Cumulative views up to this date
    cumulative_comments = db.Column(db.Integer, default=0) # Cumulative comments up to this date
    views = db.Column(db.Integer, default=0) # New views for this date
    comments = db.Column(db.Integer, default=0) # New comments for this date

    def __repr__(self):
        return f'<Tag {self.name}>'

    __table_args__= (
        UniqueConstraint('date', name='uq_date_daily_stats'),
    )

# User Loader
class User(UserMixin, db.Model): # pylint: disable=R0903
    """Model for the Users table.
       This Table is used to handle logging in users.
    """
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    # Link to the Role table
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id', name="fk_role_id_users"))

    role = db.relationship('Role', backref='users') # Releationship to Role

    def __repr__(self):
        return f'<User {self.username}>'

    __table_args__= (
        UniqueConstraint('username', name='uq_name_users'),
    )

    @property
    def is_admin(self):
        """Used to test roles that the user has and check if they're allowed
           To do various activities.
        """
        return self.role.name == 'admin'

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    """Logs in user"""
    return db.session.get(User, user_id)

### Public Routing

@app.route('/')
def home():
    """Routing for the homepage.
       Will display all current posts ordered by newest post.
       Also displays a dropdown menu for selecting tags to filter posts
       by desired topics.
    """
    # Query all posts from the database
    posts = Post.query.order_by(Post.date.desc()).all() # Fetch all posts ordered by newest date

    return render_template('base.html', posts=posts)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Routing to allow for the admin to log in.
       Brings up the login page which provides a form for providing
       credentials.
       Very basic authentication, for the moment.
    """

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        byte_password = password.encode('utf-8')

        user = db.session.scalars(
                db.select(User).filter_by(username=username).limit(1)
            ).first()

        if user and bcrypt.checkpw(byte_password, user.password_hash.encode('utf-8')):
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid credentials. Please try again')

    return render_template('login.html')

@app.route('/view_post/<int:post_id>')
def view_post(post_id):
    """Routing for viewing individual posts.
       Will display the posts content as well as show
       all associated tags.
    """

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

    if not current_user.is_authenticated or not current_user.is_admin:
        # Increment the view count on posts
        post.view_count += 1

        # Increment the view count for each tag attached to the post
        # This gets the tag objects whose ids match the ids in our list
        tags = db.session.query(Tag).filter(Tag.id.in_(tag_ids)).all()

        for tag in tags:
            tag.view_count += 1

        db.session.commit()

    return render_template('view_post.html', post=post, tags=tags)

@app.route('/fetch_tags', methods=['GET'])
def fetch_tags():
    """API Endpoint for fetching all of the tags.
       Used on the home page to allow filtering as well as
       to populate the manage_tags page.
    """

    with app.app_context():
        tags = db.session.execute(
                        db.select(Tag)
                    ).scalars().all()

    tags_list = [{'id': tag.id, 'name': tag.name, 'view_count': tag.view_count} for tag in tags]

    return jsonify({'tags': tags_list})

@app.route('/fetch_posts_by_tags', methods=['GET'])
def fetch_posts_by_tags():
    """API Endpoint for filtering posts by tags.
       Used for filtering via tag selection on the home page.
       Multiple tags can be selected and posts with any of the 
       selected tags will appear, ordered by newest post
    """

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

    post_list = [
        {'id': post.id, 'title': post.title, 'date': post.date} for post in unique_posts.values()
    ]

    return jsonify({'posts': post_list})

@app.route('/fetch_all_posts', methods=['GET'])
def fetch_all_posts():
    """API endpoint for fetching all posts.
       Used to populate the homepage.
    """
    posts = Post.query.order_by(Post.date.desc()).all() # Fetch all posts ordered by newest date

    post_list = [{'id': post.id, 'title': post.title, 'date': post.date} for post in posts]

    return jsonify({'posts': post_list})

@app.route('/add_comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    """Routing allows for anyone viewing a post to add a comment
       to the comment section at the bottom of the page.
       A title and message are required to make a post.
       A date is automatically attached to the comment.
       Redirects to viewing the post so user can see their comment
       has been added.
    """
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

@app.route('/dashboard')
@login_required
def dashboard():
    """Routing method for the admin dashboard.
       Here is where the admin can go to get stats about
       their blog site.

       This is for top 5 posts and tags in terms of view count
       A pie chart for tag popularity, again by view count
       A bar graph to display daily engagement by views and comments per day
    """
    if not current_user.is_admin:
        return redirect(url_for('index')) # Redirect non-admins to the homepage

    # Fetch analytics data (ex: top viewed posts/tags, daily stats)
    top_posts = db.session.query(Post).order_by(Post.view_count.desc()).limit(5).all()
    top_tags = db.session.query(Tag).order_by(Tag.view_count.desc()).limit(5).all()

    # Fetch data for top tags chart
    tags = db.session.query(Tag).all()
    tag_names = [tag.name for tag in tags]
    tag_views = [tag.view_count for tag in tags]

    # Generate tag pie chart using Plotly
    tag_popularity_figure = px.pie(
        names = tag_names,
        values = tag_views,
        title = 'Popularity of Tags by Views'
    )

    # Generate html for daily engagement graph
    daily_engagement_graph = generate_daily_engagement_graph()

    tag_popularity_graph = tag_popularity_figure.to_html(full_html=False)

    return render_template(
        'dashboard.html',
         top_posts=top_posts,
         top_tags=top_tags,
         tag_popularity_graph=tag_popularity_graph,
         daily_engagement_graph=daily_engagement_graph
         )

@app.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    """Routing enables the admin to create a new Post.
       Requires a title, content, and date. The date is automatically selected as today.
       Optionally, tags can be applied to the post for ease of filtering content.
       Notibly this will also help to format seperate paragraphs and could be a place to add
       Additonal formatting options in the future.
       Returns the admin to the home page to continue navigating the app.
    """
    if request.method == 'POST':
        post_title = request.form['title']
        post_content = request.form['content']
        date_string = request.form['date']

        # Retrieve the tags string and split it into a list
        # Split the comma-separated string into a list
        selected_tags = request.form['tags'].split(',')

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
    """Routing allows for the admin to edit a post
       Tags are automatically removed and then must be reselected.
       Can be used to add additional tags to a post.
       Page provides the admin with ability to delete the post and/or comments attached
    """
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
    """Routing allows for the deletion of a comment by the admin
       Reloads edit page so admin can chain delete comments if necessary
    """
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
    """Routing to delete a post. Requires admin.
       Deleting a post will delete the row from the relationship table PostTags
       Any tags that are orphaned by this operation are also removed to tidy up.
       Returns the admin to the home page for easy navigation to next task
    """
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
    orphan_tags = db.session.query(Tag).outerjoin(PostTags).filter(PostTags.post_id.is_(None)).all()

    for tag in orphan_tags:
        db.session.delete(tag)

    db.session.commit()

    flash('Post deleted successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/manage_tags')
@login_required
def manage_tags():
    """Routing to direct the admin to a special page for viewing
       how each tag is utilized, allows the admin to delete tags,
       and can be used to create new tags
    """
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
    """Routing to remove a tag from the database
       Additionally this will remove rows from PostTags removing a link between
       Post(s) and the deleted Tag
    """
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
    """Routing to create and add a tag to the database
       Tags are used to highlight topics within a post
    """
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
            new_tag = Tag(name=tag_name)
            db.session.add(new_tag)
            db.session.commit()
            flash('Tag created successfully!', 'success')

        with app.app_context():
            tags = db.session.execute(
                            db.select(Tag)
                        ).scalars().all()

        return render_template('manage_tags.html', tags=tags), 201

    return redirect(url_for('home'), 405)

@app.route('/debug_posts')
@login_required
def debug_posts():
    """Routing to visually test if posts appear on screen"""
    # Query all posts from the database
    posts = Post.query.all()  # Fetch all posts

    # Render a simple template to display the posts
    return render_template('debug_posts.html', posts=posts)


@app.route('/logout')
@login_required
def logout():
    """Routing to log the user out"""
    logout_user()
    return redirect(url_for('login'))

def generate_daily_engagement_graph():
    """Helper function used during generation of the
       template to render during the dashboard routing.
       This was just really a lot to bite off inside of the
       parent method and I thought I'd hide the magic a bit
       to keep the routing more legible.
    """
    # Get data from database
    daily_stats = db.session.query(DailyStats).all()

    # Populate values for the graph
    dates = [stat.date for stat in daily_stats]
    daily_views = [stat.views for stat in daily_stats]
    daily_comments = [-stat.comments for stat in daily_stats] # Negative so they go down

    # Make a graph object
    daily_stats_figure = go.Figure()

    # Draw Views in Green
    daily_stats_figure.add_trace(go.Bar(
        x=dates,
        y=daily_views,
        name='Views',
        marker_color='green'
    ))

    # Draw Comments in Blue
    daily_stats_figure.add_trace(go.Bar(
        x=dates,
        y=daily_comments,
        name='Comments',
        marker_color='blue'
    ))

    # Fix the layout a bit
    daily_stats_figure.update_layout(
        title='Daily Views and Comments',
        xaxis_title='Date',
        yaxis_title='Count',
        barmode='overlay', # Overlay bars to avoid stacking
        bargap=0.2,        # Gap between bars
        yaxis={
            'title': 'Views and Comments',
            'autorange': True
        }
    )

    return daily_stats_figure.to_html(full_html=False)

if __name__ == "__main__":

    ###For development only remove for production
    with app.app_context():
        db.create_all()
    ###

    app.run(debug=True, port=5000)
