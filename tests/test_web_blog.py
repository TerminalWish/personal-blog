import unittest
from bs4 import BeautifulSoup
from web_blog import Post, Tag, Comment, PostTags, Message, app, db

class TestWebBlog(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # Use an in-memory database for tests

        with app.app_context():
            db.create_all()

        cls.app = app.test_client()
        cls.app.testing = True

    @classmethod
    def login_as_admin(cls):
        """Helper function to log in as the admin user."""
        with cls.app:
            cls.app.post('/login', data={
                'username': 'admin',
                'password': 'password'
            })

    @classmethod
    def logout_user(cls):
        """Helper function to log out the current user."""
        with cls.app:
            cls.app.get('/logout')

    @classmethod
    def create_test_tag(cls, test_tag_name):
        """Helper function to create a tag in the tags table for testing"""
        with app.app_context():
            test_tag = Tag(name=test_tag_name)
            db.session.add(test_tag)
            db.session.commit()

    @classmethod
    def remove_test_tag(cls, test_tag_name):
        """Helper function to remove a tag used in testing"""
        if test_tag_name == "Testing":
            return
        with app.app_context():
            test_tag = db.session.scalars(
                db.select(Tag).filter_by(name=f'{test_tag_name}').limit(1)
            ).first()
            db.session.delete(test_tag)
            db.session.commit()

    @classmethod
    def remove_test_post(cls, test_post_name):
        """Helper function to remove a post used in testing"""
        with app.app_context():
            test_post = db.session.scalars(
                db.select(Post).filter_by(title=f'{test_post_name}').limit(1)
            ).first()

            db.session.delete(test_post)
            db.session.commit()

    # Creation Tests
    def test_create_message(self):

        #Login
        self.login_as_admin()

        # create the message
        test_message_subject = 'test subject'
        test_message_message = 'this is a test message'
        test_message_contact = 'test contact #'
        response = self.app.post('/message_me', data={
            'subject': test_message_subject,
            'message': test_message_message,
            'contact_info': test_message_contact
        })

        self.assertEqual(response.status_code, 302)

        with app.app_context():
            test_message = Message.query.filter_by(subject=test_message_subject).first()
            self.assertIsNotNone(test_message)
            self.assertEqual(test_message_message, test_message.message)
            self.assertEqual(test_message_contact, test_message.contact_info)

        # Cleanup
        with app.app_context():
            db.session.delete(test_message)
        
        self.logout_user

    def test_add_tag_to_post(self):
        
        #Login
        self.login_as_admin()

        test_tag_name = 'Tag-san'

        self.create_test_tag(test_tag_name)

        # create a new post
        test_post_name = 'Test Post'
        self.app.post('/create_post', data={
            'title': test_post_name,
            'content': 'This is a test content.',
            'date': '2024-10-12',
            'tags': ''
        })

        with app.app_context():
            test_post = Post.query.filter_by(title=test_post_name).first()
            self.assertIsNotNone(test_post)
            test_tag = Tag.query.filter_by(name=test_tag_name).first()
            self.assertIsNotNone(test_tag)

        test_list = [test_tag.id]
        response = self.app.post(f'/edit_post/{test_post.id}', data={
            'title': test_post.title,
            'content': test_post.content,
            'date': test_post.date,
            'tags': test_list
        })

        self.assertEqual(response.status_code, 302)

        # Check for the updated link
        with app.app_context():
            test_post_tag = PostTags.query.filter_by(post_id=test_post.id).first()
            test_tag_post = PostTags.query.filter_by(tag_id=test_tag.id).first()
            self.assertEqual(test_post_tag, test_tag_post)

        # Cleanup
        self.remove_test_post(test_post_name)
        self.remove_test_tag(test_tag_name)
        self.logout_user()

    def test_add_comment(self):
        self.login_as_admin()

        # create a new post
        self.app.post('/create_post', data={
            'title': 'Test Post',
            'content': 'This is a test content.',
            'date': '2024-10-12',
            'tags': ''
        })

        with app.app_context():
            post = Post.query.filter_by(title='Test Post').first()

        # Create the comment
        response = self.app.post(f'/add_comment/{post.id}', data={
            'title': 'Test Comment',
            'content': 'Testing comment section'
        })

        self.assertEqual(response.status_code, 302)

        with app.app_context():
            comment = Comment.query.filter_by(title='Test Comment').first()
            self.assertIsNotNone(comment) #A comment was created
            self.assertEqual(comment.content, 'Testing comment section') #Comment content copied successfully
            self.assertEqual(comment.post_id, post.id) #Comment attached to correct post
        
        # Remove test post
        self.remove_test_post('Test Post')

        with app.app_context():
            comment = Comment.query.filter_by(title='Test Comment').first()
            self.assertIsNone(comment) #Comment was orphaned by post delete so it was removed

        self.logout_user()

    def test_create_tag(self):
        # Test creating without permission
        test_tag_name = 'Tag-san'
        response = self.app.post('/create_tag', data={
            'tag_name': test_tag_name
        })

        self.assertEqual(response.status_code, 401)

        # Login
        self.login_as_admin()

        # Test creating a new tag
        response = self.app.post('/create_tag', data={
            'tag_name': test_tag_name
        })

        self.assertEqual(response.status_code, 201)

        # Check if the tag was added
        with app.app_context():
            tag = Tag.query.filter_by(name=test_tag_name).first()
            self.assertIsNotNone(tag) # Ensure it exists
            self.assertEqual(tag.name, test_tag_name)

        # Remove the test tag
        self.remove_test_tag(test_tag_name)

        # Logout
        self.logout_user()

    def test_create_post(self):
        # Login
        self.login_as_admin()

        # Test creating a new post
        response = self.app.post('/create_post', data={
            'title': 'Test Post',
            'content': 'This is a test content.',
            'date': '2024-10-12',
            'tags': ''
        })
        
        self.assertEqual(response.status_code, 302)  # Check for a redirect after successful post creation

        # Check if the post was added to the database
        with app.app_context():
            post = Post.query.filter_by(title='Test Post').first()
            self.assertIsNotNone(post)  # Ensure the post exists
            self.assertEqual(post.content, 'This is a test content.')

        # Remove test post
        self.remove_test_post('Test Post')
        
        # Logout
        self.logout_user()

    def test_add_post_with_tag(self):

        #Login
        self.login_as_admin()

        test_tag_name = 'Tag-san'

        self.create_test_tag(test_tag_name)

        with app.app_context():
            test_tag = Tag.query.filter_by(name=test_tag_name).first()
            self.assertIsNotNone(test_tag)

        test_tag_list = [test_tag.id]

        # create a new post
        test_post_name = 'Test Post'
        response = self.app.post('/create_post', data={
            'title': test_post_name,
            'content': 'This is a test content.',
            'date': '2024-10-12',
            'tags': test_tag_list
        })

        self.assertEqual(response.status_code, 302)

        with app.app_context():
            test_post = Post.query.filter_by(title=test_post_name).first()
            self.assertIsNotNone(test_post)
        
        # Check for post-tag link
        with app.app_context():
            test_post_tag = PostTags.query.filter_by(post_id=test_post.id).first()
            test_tag_post = PostTags.query.filter_by(tag_id=test_tag.id).first()
            self.assertEqual(test_post_tag, test_tag_post) #The whole test -_-

        # Cleanup
        self.remove_test_post(test_post_name)
        self.remove_test_tag(test_tag_name)
        self.logout_user()

    # Deletion Tests
    def test_delete_comment(self):
        # Login
        self.login_as_admin()
        
        # Test creating a new post
        test_post_name = 'Test Post'
        response = self.app.post('/create_post', data={
            'title': test_post_name,
            'content': 'This is a test content.',
            'date': '2024-10-12',
            'tags': ''
        })

        self.assertEqual(response.status_code, 302)  # Check for a redirect after successful post creation

        with app.app_context():
            test_post = db.session.scalars(
                    db.select(Post).filter_by(title=f'{test_post_name}').limit(1)
                ).first()
            
            # Create the test comment
            test_comment_name = "Test Comment"
            test_comment = Comment(
                    post_id=test_post.id,
                    title=test_comment_name,
                    content="Test comment content"
                )
            db.session.add(test_comment)
            db.session.commit()

            creation_test = Comment.query.filter_by(title=test_comment_name).first()
            self.assertIsNotNone(creation_test)

        # Logout
        self.logout_user()
        response = self.app.post(f'/delete_comment/{test_comment.id}')

        self.assertEqual(response.status_code, 401) #Insufficent permissions

        # Log back in
        self.login_as_admin()

        response = self.app.post(f'/delete_comment/{test_comment.id}')

        self.assertEqual(response.status_code, 204) #Found and deleted

        with app.app_context():
            creation_test = Comment.query.filter_by(title=test_comment_name).first()
            self.assertIsNone(creation_test) # It's actually gone
            post_exists_test = Post.query.filter_by(title=test_post_name).first()
            self.assertIsNotNone(post_exists_test) # Post wasn't deleted by rogue cascade event

        response = self.app.post(f'/delete_comment/9999')

        self.assertEqual(response.status_code, 404) #Not found

        # Cleanup
        self.remove_test_post(test_post_name)
        self.login_as_admin

    def test_delete_post(self):
        # Login
        self.login_as_admin()

        # Test creating a new post
        response = self.app.post('/create_post', data={
            'title': 'Test Post',
            'content': 'This is a test content.',
            'date': '2024-10-12',
            'tags': ''
        })

        self.assertEqual(response.status_code, 302)  # Check for a redirect after successful post creation


        # Test with permission
        with app.app_context():
            post = Post.query.filter_by(title='Test Post').first()

        response = self.app.post(f'/delete_post/{post.id}')

        self.assertEqual(response.status_code, 302)

        # Test with missing id
        response = self.app.post(f'/delete_post/9999')

        self.assertEqual(response.status_code, 404)

        # Logout
        self.logout_user()

    def test_delete_tag(self):
        # Create a test tag to delete
        test_tag_name = 'Tag-san'

        self.create_test_tag(test_tag_name)

        # Test without permission
        with app.app_context():
            tag = Tag.query.filter_by(name=test_tag_name).first()

        response = self.app.post(f'/delete_tag/{tag.id}')

        self.assertEqual(response.status_code, 401)

        # Login
        self.login_as_admin()

        # Test with permission
        with app.app_context():
            tag = Tag.query.filter_by(name=test_tag_name).first()

        response = self.app.post(f'/delete_tag/{tag.id}')

        self.assertEqual(response.status_code, 204)

        # Test with missing tag
        response = self.app.post(f'/delete_tag/9999')

        self.assertEqual(response.status_code, 404)

    def test_delete_post_cascade_delete_orphaned_tag(self):
        #Login
        self.login_as_admin()

        test_tag_name = 'Tag-san 5'

        self.create_test_tag(test_tag_name)

        with app.app_context():
            test_tag = Tag.query.filter_by(name=test_tag_name).first()
            self.assertIsNotNone(test_tag)

        test_tag_list = [test_tag.id]

        # create a new post
        test_post_name = 'Test Post 5'
        response = self.app.post('/create_post', data={
            'title': test_post_name,
            'content': 'This is a test content.',
            'date': '2024-10-12',
            'tags': test_tag_list
        })

        self.assertEqual(response.status_code, 302)

        with app.app_context():
            test_post = Post.query.filter_by(title=test_post_name).first()
            self.assertIsNotNone(test_post)

        # Delete post, orphaning tag
        response = self.app.post(f'/delete_post/{test_post.id}')
        self.assertEqual(response.status_code, 302) # Redirect home

        with app.app_context():
            test_post = Post.query.filter_by(title=test_post_name).first()
            self.assertIsNone(test_post)
            test_tag = Tag.query.filter_by(name=test_tag_name).first()
            self.assertIsNone(test_tag) # This guy shouldn't exist

        # Cleanup
        self.logout_user()

    def test_delete_post_do_not_delete_non_orphaned_tag(self):
        #Login
        self.login_as_admin()

        test_tag_name = 'Tag-san'

        self.create_test_tag(test_tag_name)

        with app.app_context():
            test_tag = Tag.query.filter_by(name=test_tag_name).first()
            self.assertIsNotNone(test_tag)

        test_tag_list = [test_tag.id]

        # create two new posts and attach tag to both
        test_post_name = 'Test Post'
        response = self.app.post('/create_post', data={
            'title': test_post_name,
            'content': 'This is a test content.',
            'date': '2024-10-12',
            'tags': test_tag_list
        })

        self.assertEqual(response.status_code, 302)

        test_post_name_two = "Test Post 2"
        response = self.app.post('/create_post', data={
            'title': test_post_name_two,
            'content': 'This is a test content.',
            'date': '2024-10-12',
            'tags': test_tag_list
        })

        self.assertEqual(response.status_code, 302)

        with app.app_context():
            test_post = Post.query.filter_by(title=test_post_name).first()
            self.assertIsNotNone(test_post)

        # Delete post, routing will delete an orphaned tag
        response = self.app.post(f'/delete_post/{test_post.id}')
        self.assertEqual(response.status_code, 302) # Redirect home

        with app.app_context():
            #First post was deleted
            test_post = Post.query.filter_by(title=test_post_name).first()
            self.assertIsNone(test_post)
            #Second post not deleted
            test_post = Post.query.filter_by(title=test_post_name_two).first()
            self.assertIsNotNone(test_post)
            test_tag = Tag.query.filter_by(name=test_tag_name).first()
            self.assertIsNotNone(test_tag) # This guy should still exist

        # Cleanup
        self.app.post(f'/delete_post/{test_post.id}') #Deletes second post and tag
        self.logout_user()

    # Routing Tests
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

    def test_login(self):
        response = self.app.get('/login')
        self.assertEqual(response.status_code, 200) #Successful response

    def test_debug_posts(self):
        # Login
        self.login_as_admin()

        # Test accessing the debug posts route
        response = self.app.get('/debug_posts')
        self.assertEqual(response.status_code, 200)  # Ensure the page loads successfully

        # Logout
        self.logout_user()

    def test_edit_post(self):
        # Login
        self.login_as_admin()

        # Test creating a new post
        response = self.app.post('/create_post', data={
            'title': 'Test Post',
            'content': 'This is a test content.',
            'date': '2024-10-12',
            'tags': ''
        })

        self.assertEqual(response.status_code, 302)  # Check for a redirect after successful post creation

        with app.app_context():
            post = db.session.scalars(
                db.select(Post).filter_by(title='Test Post').limit(1)
            ).first()

        self.assertIsNotNone(post)  # Ensure the post exists
        post_id = post.id

        response = self.app.get(f'/edit_post/{post_id}')
        self.assertEqual(response.status_code, 200) # It should be there

        # Verify content in the response
        self.assertIn(b'Test Post', response.data) # Check if the title is present
        self.assertIn(b'This is a test content', response.data) # Check if the content is present

        # Data to update the post
        updated_data = {
            'title': 'New Title',
            'content': 'New Content',
            'date': '2024-10-12',
            'tags': ''  # If you are sending a list of tags as a comma-separated string
        }

        response = self.app.post(f'/edit_post/{post_id}', data=updated_data)

        self.assertEqual(response.status_code, 302)

        with app.app_context():
            updated_post = db.session.scalars(
                db.select(Post).filter_by(id=post_id).limit(1)
            ).first()

        self.assertEqual(updated_post.title, 'New Title')
        self.assertEqual(updated_post.content, 'New Content')

        # Remove test post
        self.remove_test_post(updated_post.title)

    def test_manage_tags(self):
        #check permissions first
        response = self.app.get('/manage_tags')

        self.assertEqual(response.status_code, 401)

        self.login_as_admin()

        #create a test tag
        test_tag_name = 'Tag-san'
        self.create_test_tag(test_tag_name)

        #Retrieve tags from db
        with app.app_context():
            tags = db.session.execute(
                db.select(Tag)
            ).scalars().all()

        # Check for presence in the database
        self.assertTrue(any(tag.name == test_tag_name for tag in tags), "Test tag not found in the database.")

        # Check the response after accessing the manage tags page
        response = self.app.get('/manage_tags')
        self.assertEqual(response.status_code, 200)

        soup = BeautifulSoup(response.data, 'html.parser')

        tag_card = soup.find('div', class_='tag-card', string='Tag-san')
        self.assertIsNone(tag_card, "Test tag card not found in the response.")

        # Verify that the tag is present in the response
        #self.assertIn(test_tag_name.encode('utf-8'), response.data, "Test tag not found in the response.")

        #remove the test tag
        self.remove_test_tag(test_tag_name)

    def test_view_post_valid_id(self):
        self.login_as_admin()

        # Test creating a new post
        response = self.app.post('/create_post', data={
            'title': 'Test Post',
            'content': 'This is a test content.',
            'date': '2024-10-12',
            'tags': ''
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

        # Remove test post
        self.remove_test_post(post.title)

        # Logout
        self.logout_user()

    def test_view_post_invalid_id(self):
        #Test invalid post ID
        response = self.app.get('/view_post/9999') # Required: ID that does not exist
        self.assertEqual(response.status_code, 404) # Should throw 404 if not in db

    def test_base(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200) #Successful response
        #TODO test for page content --> self.assertIn([text], response.data)

    # API Endpoint Tests
    def test_fetch_tags(self):
        tag_name = ''
        for i in range(0, 5):
            tag_name = f"Tag-san {i}"
            self.create_test_tag(tag_name)

        response = self.app.get('/fetch_tags')
        
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        
        # Assertions on the data
        self.assertIn('tags', data)  # Check that the 'tags' key exists
        self.assertIsInstance(data['tags'], list)  # Ensure it's a list

        # Create a list of tag names found
        found_tag_names = [tag['name'] for tag in data['tags']]

        for j in range(0, 5):
            tag_name = f"Tag-san {j}"
            self.assertIn(tag_name, found_tag_names)
            self.remove_test_tag(tag_name)

    def test_fetch_posts_by_tags(self):
        self.login_as_admin()

        test_tag_name = "Tag-san"

        self.create_test_tag(test_tag_name)

        with app.app_context():
            test_tag = db.session.scalars(
                db.select(Tag).filter_by(name=f'{test_tag_name}').limit(1)
            ).first()

        test_post_names = ["TP 1", "TP 2", "TP 3"]
        for post_name in test_post_names:
            self.app.post('/create_post', data={
                'title': post_name,
                'content': 'This is a test content.',
                'date': '2024-10-12',
                'tags': test_tag.id
            })

        response = self.app.get(f'/fetch_posts_by_tags?ids={test_tag.id}')

        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        # Assertions on the data
        self.assertIn('posts', data)  # Check that the 'tags' key exists
        self.assertIsInstance(data['posts'], list)  # Ensure it's a list

        found_test_post_names = [post['title'] for post in data['posts']]

        for test_post_name in test_post_names:
            self.assertIn(test_post_name, found_test_post_names)
            self.remove_test_post(test_post_name)

        self.remove_test_tag(test_tag_name)

        self.logout_user()

    def test_fetch_all_posts(self):

        self.login_as_admin()

        test_post_names = ["TP 1", "TP 2", "TP 3"]
        for post_name in test_post_names:
            self.app.post('/create_post', data={
                'title': post_name,
                'content': 'This is a test content.',
                'date': '2024-10-12',
                'tags': ''
            })

        response = self.app.get('/fetch_all_posts')

        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        # Assertions on the data
        self.assertIn('posts', data)  # Check that the 'tags' key exists
        self.assertIsInstance(data['posts'], list)  # Ensure it's a list

        found_test_post_names = [post['title'] for post in data['posts']]

        for test_post_name in test_post_names:
            self.assertIn(test_post_name, found_test_post_names)
            self.remove_test_post(test_post_name)

        self.logout_user

if __name__ == "__main__":
    unittest.main()