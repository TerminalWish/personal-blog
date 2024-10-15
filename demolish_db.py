from web_blog import User, Role, app, db
from sqlalchemy import text

if __name__ == "__main__":
    with app.app_context():
        db.session.execute(text('DROP TABLE users;'))
        db.session.execute(text('DROP TABLE roles;'))
        db.session.commit()

    app.run(debug=True, port=5000)