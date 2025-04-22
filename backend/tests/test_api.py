import unittest
import json
import os
from datetime import date
from backend.app import app, user_manager, family_tree  # Import your Flask app
from backend.src.user_management import UserManagement
from backend.src.family_tree import FamilyTree


class TestAPI(unittest.TestCase):
    test_users = [
        {"username": "testuser1", "password": "testpassword1", "role": "basic"},
        {"username": "testuser2", "password": "testpassword2", "role": "admin"},
    ]
    test_people = [
        {"first_name": "John", "last_name": "Doe", "birth_date": "1980-01-01"},
        {"first_name": "Jane", "last_name": "Doe", "birth_date": "1982-02-02"},
    ]
    test_relationships = [
        {"person1_id": None, "person2_id": None, "rel_type": "spouse"},
    ]

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['DEBUG'] = False
        self.app = app.test_client()
        self.user_manager = user_manager
        self.family_tree = family_tree
        self.create_test_data()

    def tearDown(self):
        self.delete_test_data()

    def create_test_data(self):
        for user_data in self.test_users:
            user = self.user_manager.register_user(user_data["username"], user_data["password"], user_data["role"])
        for person_data in self.test_people:
            person = self.family_tree.add_person(
                person_data["first_name"], person_data["last_name"], dob=person_data["birth_date"]
            )
        self.test_relationships[0]["person1_id"] = list(self.family_tree.people.keys())[0]
        self.test_relationships[0]["person2_id"] = list(self.family_tree.people.keys())[1]
        self.family_tree.add_relationship(
            self.test_relationships[0]["person1_id"], self.test_relationships[0]["person2_id"], "spouse"
        )

    def delete_test_data(self):
        for user_data in self.test_users:
            user = self.user_manager.find_user_by_username(user_data["username"])
            if user:
                self.user_manager.delete_user(user.user_id, "test_teardown")
        for person_id in list(self.family_tree.people.keys()):
            self.family_tree.delete_person(person_id, "test_teardown")

    def login(self, username, password):
        response = self.app.post(
            "/api/login",
            data=json.dumps({"username": username, "password": password}),
            content_type="application/json",
        )
        return response

    def logout(self):
        response = self.app.post("/api/logout")
        return response

    def test_api_session_not_authenticated(self):
        response = self.app.get("/api/session")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(data["isAuthenticated"], False)
        self.assertEqual(data["user"], None)

    def test_api_login(self):
        # Correct login
        response = self.login(self.test_users[0]["username"], self.test_users[0]["password"])
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data["message"])

        # Wrong password
        response = self.login(self.test_users[0]["username"], "wrong_password")
        self.assertEqual(response.status_code, 401)

        # Wrong username
        response = self.login("wrong_username", self.test_users[0]["password"])
        self.assertEqual(response.status_code, 401)

    def test_api_register(self):
        # Correct register
        new_user_data = {"username": "newuser", "password": "newpassword"}
        response = self.app.post(
            "/api/register", data=json.dumps(new_user_data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data["message"])

        # Already registered
        response = self.app.post(
            "/api/register", data=json.dumps(new_user_data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 409)

        # Missing data
        response = self.app.post("/api/register", data=json.dumps({}), content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_api_logout(self):
        # Login
        self.login(self.test_users[0]["username"], self.test_users[0]["password"])
        # Logout
        response = self.logout()
        self.assertEqual(response.status_code, 200)

    def test_api_people(self):
        # Login
        self.login(self.test_users[0]["username"], self.test_users[0]["password"])
        # GET all people
        response = self.app.get("/api/people")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(len(data), 2)
        # POST
        new_person_data = {"first_name": "New", "last_name": "Person", "birth_date": "2000-01-01"}
        response = self.app.post(
            "/api/people", data=json.dumps(new_person_data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        # GET one person
        person_id = json.loads(response.get_data(as_text=True))["person_id"]
        response = self.app.get(f"/api/people/{person_id}")
        self.assertEqual(response.status_code, 200)
        # PUT
        edit_person_data = {"first_name": "Edited", "last_name": "Person"}
        response = self.app.put(
            f"/api/people/{person_id}", data=json.dumps(edit_person_data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        # DELETE
        response = self.app.delete(f"/api/people/{person_id}")
        self.assertEqual(response.status_code, 204)
        # Logout
        self.logout()

    def test_api_relationships(self):
        # Login
        self.login(self.test_users[0]["username"], self.test_users[0]["password"])
        # GET all relationships
        response = self.app.get("/api/relationships")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(len(data), 1)
        # POST
        new_relationship_data = {
            "person1_id": list(self.family_tree.people.keys())[0],
            "person2_id": list(self.family_tree.people.keys())[1],
            "rel_type": "sibling",
        }
        response = self.app.post(
            "/api/relationships", data=json.dumps(new_relationship_data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)  # Already exists a relationship
        new_person_data = {"first_name": "New", "last_name": "Person", "birth_date": "2000-01-01"}
        response = self.app.post(
            "/api/people", data=json.dumps(new_person_data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        new_relationship_data["person2_id"] = json.loads(response.get_data(as_text=True))["person_id"]
        response = self.app.post(
            "/api/relationships", data=json.dumps(new_relationship_data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        # PUT
        relationship_id = list(self.family_tree.relationships.keys())[1]
        edit_relationship_data = {"rel_type": "cousin"}
        response = self.app.put(
            f"/api/relationships/{relationship_id}",
            data=json.dumps(edit_relationship_data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        # DELETE
        response = self.app.delete(f"/api/relationships/{relationship_id}")
        self.assertEqual(response.status_code, 204)
        # Logout
        self.logout()

    def test_api_tree_data(self):
        # Login
        self.login(self.test_users[0]["username"], self.test_users[0]["password"])
        # GET
        response = self.app.get("/api/tree_data")
        self.assertEqual(response.status_code, 200)
        # Logout
        self.logout()

    def test_api_password_reset(self):
        # Request password reset
        response = self.app.post(
            "/request_password_reset", data=json.dumps({"email": self.test_users[0]["username"]}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        # Reset password
        user = self.user_manager.find_user_by_username(self.test_users[0]["username"])
        token = user.reset_token
        response = self.app.post(
            f"/reset_password/{token}", data=json.dumps({"new_password": "new_password"}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)