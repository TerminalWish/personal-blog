from web_blog import User, Role, app, db

def create_default_roles():
    admin_role = Role(name='admin')
    guest_role = Role(name='guest')  # Another default role

    db.session.add(admin_role)
    db.session.add(guest_role)
    db.session.commit()

def create_admin_user():
    # Assuming you want to hash the password for security
    hashed_password = 'password'  # Replace with actual hashing

    admin_user = User(username='admin', password_hash=hashed_password, role_id=1)  # 1 is the ID for admin
    db.session.add(admin_user)
    db.session.commit()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Create all tables
        create_default_roles()  # Populate roles
        create_admin_user()  # Create the admin user
    #app.run(debug=True, port=5000)
