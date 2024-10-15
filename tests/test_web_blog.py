import unittest
from web_blog import Post, app, db

class TestWebBlog(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # Use an in-memory database for tests
    
        with app.app_context():
            db.create_all()

        cls.app = app.test_client()
        cls.app.testing = True

    def test_view_post_valid_id(self):
        # Login
        response = self.app.post('/login', data={
            'username': 'admin',
            'password': 'password'
        })

        self.assertEqual(response.status_code, 302)

        # Test creating a new post
        response = self.app.post('/create_post', data={
            'title': 'Test Post',
            'content': 'This is a test content.',
            'date': '2024-10-12'
        })

        self.assertEqual(response.status_code, 302)  # Check for a redirect after successful post creation
        
        # Check if the post was added to the database
        with app.app_context():
            #I won't pretend to understand it, but SQLAlchemy 2.0 documentation suggested that the below is equivalent
            #post = Post.query.filter_by(title='Test Post').first()
            post = db.session.scalars(
                db.select(Post).filter_by(title='Test Post').limit(1)
            ).first()
            
            self.assertIsNotNone(post)  # Ensure the post exists
            post_id = post.id


        response = self.app.get(f"/view_post/{post_id}")
        self.assertEqual(response.status_code, 200) # It should be there

        # Verify content in the response
        self.assertIn(b'Test Post', response.data) # Check if the title is present
        self.assertIn(b'This is a test content', response.data) # Check if the content is present

    def test_view_post_invalid_id(self):
        #Test invalid post ID
        response = self.app.get('/view_post/9999') # Required: ID that does not exist
        self.assertEqual(response.status_code, 404) # Should throw 404 if not in db

    def test_create_post(self):
        # Login
        response = self.app.post('/login', data={
            'username': 'admin',
            'password': 'password'
        })

        self.assertEqual(response.status_code, 302)

        # Test creating a new post
        response = self.app.post('/create_post', data={
            'title': 'Test Post',
            'content': 'This is a test content.',
            'date': '2024-10-12'
        })
        
        self.assertEqual(response.status_code, 302)  # Check for a redirect after successful post creation

        # Check if the post was added to the database
        with app.app_context():
            post = Post.query.filter_by(title='Test Post').first()
            self.assertIsNotNone(post)  # Ensure the post exists
            self.assertEqual(post.content, 'This is a test content.')
        
        # Logout
        response = self.app.get('/logout')
        self.assertEqual(response.status_code, 302)

    def test_debug_posts(self):
        # Login
        response = self.app.post('/login', data={
            'username': 'admin',
            'password': 'password'
        })

        self.assertEqual(response.status_code, 302)

        # Test accessing the debug posts route
        response = self.app.get('/debug_posts')
        self.assertEqual(response.status_code, 200)  # Ensure the page loads successfully

        # Logout
        response = self.app.get('/logout')
        self.assertEqual(response.status_code, 302)

    def test_base(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200) #Successful response
        #TODO test for page content --> self.assertIn([text], response.data)

    def test_login(self):
        response = self.app.get('/login')
        self.assertEqual(response.status_code, 200) #Successful response

    def test_login_with_valid_credentials(self):
        # Simulate a POST request to log in
        response = self.app.post('/login', data={
            "username": "admin",
            "password": "password"
        }, follow_redirects=True) #Follow redirects after login

        # Proper function is to leave login page and return to home
        self.assertEqual(response.status_code, 200)
        #TODO test for page content --> self.assertIn([text], response.data)
        self.assertIn(b"The Wishmaster's Codex", response.data)

        # Logout
        response = self.app.get('/logout')
        self.assertEqual(response.status_code, 302)

    def test_login_with_inalid_credentials(self):
        # Simulate a POST request to log in
        response = self.app.post('/login', data={
            "username": "admin",
            "password": "wrongpassword"
        }, follow_redirects=True) #Follow redirects after login

        # Proper function is to remain on login page
        self.assertEqual(response.status_code, 200)
        #TODO test for page content --> self.assertIn([text], response.data)
        self.assertIn(b"Invalid credentials. Please try again", response.data)

if __name__ == "__main__":
    unittest.main()