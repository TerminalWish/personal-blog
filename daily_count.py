"""A simple python script meant to keep track of view and comment
   counts for the web_blog. This script is meant to be run as a
   daily job on the server that runs the blog.
"""
from datetime import date, timedelta
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from web_blog import DailyStats, Post, Comment

# Database setup
engine = create_engine('sqlite:///instance/blog.db')
Session = sessionmaker(bind=engine)
session = Session()

def track_daily_stats(custom_date=None):
    """Simple method to track daily view and comment counts.
       This works by keeping a running talley and subtracting
       yesterday's results to get a daily count.
    """
    today = custom_date if custom_date else date.today()
    yesterday = today - timedelta(days=1)

    # Get total number of views from the Post table
    total_views = session.query(func.sum(Post.view_count)).scalar() or 0

    # Get total number of comments from the Comment table
    # Note: Pylint is upset about func.count() "not being callable"
    # This is a false positive that Pylint is catching and is a current issue
    # on Pylint's end (Issue: 8138) The code works though and Pylint doesn't
    # have an answer yet. SQLAlchemy generates queries dynamically and that's
    # messing with Pylint's static analysis.
    #total_comments = session.select(func.count()).select_from(Comment).scalar() or 0 # pylint: disable=E1102
    total_comments = session.query(func.count(Comment.id)).scalar() or 0

    # Get yesterday's stats
    yesterday_stats = session.query(DailyStats).filter_by(date=yesterday).first()

    # Calculate new views/comments for today
    if yesterday_stats:
        new_views = total_views - yesterday_stats.cumulative_views
        new_comments = total_comments - yesterday_stats.cumulative_comments
    else:
        # First day of tracking, no previous data
        new_views = total_views
        new_comments = total_comments

    # Insert today's cumulative and new stats
    new_stats = DailyStats(
        date=today,
        cumulative_views = total_views,
        cumulative_comments = total_comments,
        views = new_views,
        comments = new_comments
    )

    session.add(new_stats)
    session.commit()

if __name__ == '__main__':
    track_daily_stats(custom_date=date.today())
