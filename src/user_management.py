from src.user import User


class UserManager:
    def __init__(self):
        self.users = {}

    def create_user(self, user_id, email, password):
        if email in self.users or any(u.user_id == user_id for u in self.users.values()):
            raise ValueError("Email or user ID already in use")
        user = User(user_id, email, password)
        self.users[user.user_id] = user
        return user

    def validate_user(self, email, password):
        user = next((u for u in self.users.values() if u.email == email), None)
        if user and user.password == password:
            return user
        return None

    def promote_to_trusted(self, user_id):
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User does not exist")
        if user.trust_level >= 2:
             raise ValueError("User is already a trusted user")
        user.increase_trust_level()

    def promote_to_family_historian(self, user_id):
        user = self.users.get(user_id)
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


    def demote_to_basic(self, user_id):
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User does not exist")
        if user.role == 'basic':
            raise ValueError('User is already a basic user')
        user.set_role('basic')

    def demote_to_basic(self, user_id):
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User does not exist")
        if user.role == 'basic':
            raise ValueError('User is already a basic user')
        user.set_role('basic')

    def promote_to_administrator(self, user_id):
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User does not exist")
        if user.role == 'administrator':
            raise ValueError("User is already an administrator")
        user.set_role('administrator')
    
    def demote_to_basic(self, user_id):
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User does not exist")
        if user.role == 'basic':
            raise ValueError('User is already a basic user')
        user.set_role('basic')