import unittest
from App import app, db, User, date_of_birth_is_valid
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date


class login_authentication(unittest.TestCase):
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] =  'sqlite:///TreeGuardian.db'

        self.client = app.test_client()
        with app.app_context():
            db.drop_all()
            db.create_all()


    def test_InvalidDateOfBirth(self):
        invalid_dob = ["99-01-2002", "edji-eer-wew", "00-00-0000", "01-10-19"]

        for dob in invalid_dob:

            self.assertFalse(date_of_birth_is_valid(dob))


    def test_validDateOfBirth(self):
        valid_dob = ["2002-01-21", "2005-01-23", "2021-12-12", "2019-10-20"]

        for dob in valid_dob:

            self.assertTrue(date_of_birth_is_valid(dob))

    def test_PasswordHashingTest(self):
        password = "Preston123"
        hashed_pass = generate_password_hash(password)

        self.assertTrue(check_password_hash(hashed_pass, password))
        self.assertFalse(check_password_hash(hashed_pass, "123Preston"))

             #""" INTEGRATION TESTING """#

    def test_RegisterUserTest(self):
        response =self.client.post('/register', data={"first_name" : "Preston",
                                                      "last_name" : "De Sousa",
                                                      "username" : "prstn",
                                                      "password" : "prstn123",
                                                      "dob" : "2005-12-12"}, follow_redirects=True)

        # checking if the redirection happened and flash message displayed
        self.assertIn(b"registration successful", response.data)

        with app.app_context():
            user = User.query.filter_by(username="prstn").first()
            self.assertIsNotNone(user)


    def test_OneBlankTest(self):
        response = self.client.post('/register', data={"first_name": "",
                                                       "last_name": "smith",
                                                       "username": "john",
                                                       "password": "john123",
                                                       "dob": "2005-12-12"}, follow_redirects=True)

        self.assertIn(b"Please enter first name", response.data)

        # checking database entry.
        with app.app_context():
            user = User.query.filter_by(username="john").first()
            self.assertIsNone(user)

    def test_AllFieldsEmpty(self):
        response = self.client.post('/register', data={"first_name": "",
                                                       "last_name": "",
                                                       "username": "",
                                                       "password": "",
                                                       "dob": ""}, follow_redirects=True)

        self.assertIn(b"All fields are required!", response.data)

        with app.app_context():
            users = User.query.all()
            self.assertEqual(len(users), 0)



    def test_TestDuplicateUsername(self):
        # First registration
        self.client.post('/register', data={
            "first_name": "John",
            "last_name": "Smith",
            "username": "john123",
            "password": "password123",
            "dob": "2000-10-10"
        }, follow_redirects=True)

        # Try registering same username again
        response = self.client.post('/register', data={
            "first_name": "Jane",
            "last_name": "Doe",
            "username": "john123",
            "password": "password456",
            "dob": "1999-01-01"
        }, follow_redirects=True)

        # Check flash message
        self.assertIn(b"Username  john123 already exist", response.data)


        # Check database count
        with app.app_context():
            users = User.query.filter_by(username="john123").all()
            self.assertEqual(len(users), 1)


    def test_LoginFailedTest(self):
        with app.app_context():
            user = User(first_name="Preston",
                        last_name="De Sousa",
                        username="prstn",
                        role="user",
                        dob=date(2004,10, 4),
                        hash_password=generate_password_hash("prstn123"),
                        is_active=False)

            db.session.add(user)
            db.session.commit()

        fail_tests = [("preston", "34343"), ("prstn", "prstn234")]

        for username, password in fail_tests:
            response = self.client.post('/login', data={"username": username, "password": password}, follow_redirects=True)

            self.assertIn(b"Invalid username or password", response.data)


    def test_LoginTestSuccess(self):
        with app.app_context():
            user = User(first_name="Preston",
                        last_name="De Sousa",
                        username="prstn",
                        role="user",
                        dob=date(2004,10, 4),
                        hash_password=generate_password_hash("prstn123"),
                        is_active=False)

            db.session.add(user)
            db.session.commit()

            response = self.client.post('/login', data={"username": "prstn", "password": "prstn123"}, follow_redirects=True)

            self.assertIn(b"Welcome, prstn", response.data)

            ## chcking if the database is active

            with app.app_context():
                user = User.query.filter_by(username="prstn").first()
                self.assertTrue(user.is_active)


    def test_LogoutTest(self):
        with app.app_context():
            user = User(
                first_name="Test",
                last_name="User",
                username="testuser",
                role="user",
                dob=date(2000,1,1),
                hash_password=generate_password_hash("test123"),
                is_active=True)

            db.session.add(user)
            db.session.commit()

            ## login
            self.client.post("/login", data={"username": "testuser",
                                             "password": "test123",
                                             }, follow_redirects=True)

            #logout
            self.client.get('/logout', follow_redirects=True)

            with app.app_context():
                user = User.query.filter_by(username="testuser").first()
                self.assertFalse(user.is_active)



if __name__ == "__main__":
    unittest.main()
















