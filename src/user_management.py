from src.user import User
from datetime import timedelta

class UserManager:
    def __init__(self):
        self.users = {}

    def create_user(self, user_id, email, password, acting_user_id="system"):
        if email in self.users or any(u.user_id == user_id for u in self.users.values()):
            raise ValueError("Email or user ID already in use")
        user = User(user_id, email, password)
        self.users[user_id] = user
        return user

    def get_user(self, user_id):
        user = self.users.get(user_id)
        if user is None:
            raise ValueError("User does not exist.")
        return user
    
    def update_user(self, user_id, new_user_id, new_email, new_password):
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User does not exist.")
        user.email = new_email
        user.user_id = new_user_id

    def validate_user(self, email, password):
        user = next((u for u in self.users.values() if u.email == email), None)
        if user and user.password == password:

            return user
        return None

    def promote_to_trusted(self, user_id, acting_user_id="system"):
        user = self.users.get(user_id)
        if user.trust_level >= 2:
             raise ValueError("User is already a trusted user")
        user.increase_trust_level()

    def promote_to_family_historian(self, user_id, acting_user_id="system"):
        user = self.users.get(user_id)
        previous_user = self.users.get(user_id)
        if not user:
            raise ValueError("User does not exist")
        if user.role == 'family_historian':
            raise ValueError("User is already a family historian")
        user.set_role('family_historian')
    
    def add_trust_points(self, user_id, points):
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User does not exist")

        user.add_trust_points(points)
    
    def apply_trust_decay(self):
        for user in self.users.values():
                if user.is_inactive() and user.trust_points >= 50:
                  user.remove_trust_points(50)

    def demote_to_basic(self, user_id, acting_user_id="system"):
        previous_user = self.users.get(user_id)
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User does not exist")
        if user.role == 'basic':
            raise ValueError('User is already a basic user')
        user.set_role('basic')
    
    def promote_to_administrator(self, user_id, acting_user_id="system"):
        previous_user = self.users.get(user_id)
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User does not exist")
        if user.access_level == 'administrator':
            raise ValueError("User is already an administrator")
        user.access_level = 'administrator'

    def delete_user(self, user_id, acting_user_id="system"):
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User does not exist.")
        del self.users[user_id]

        