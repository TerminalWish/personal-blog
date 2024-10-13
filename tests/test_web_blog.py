import unittest
from web_blog import app

class TestWebBlog(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = app.test_client()
        cls.app.testing = True

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
        self.assertIn(b"Welcome to My Blog!", response.data)

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