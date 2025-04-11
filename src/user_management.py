from src.user import User

class UserManager:
    def __init__(self):
        self.users = {}

    def create_user(self, user_id, email, password):
        if email in self.users:
            raise ValueError("Email already in use")
        user = User(user_id, email, password)
        self.users[email] = user
        return user

    def validate_user(self, email, password):
        user = self.users.get(email)
        if user and user.password == password:
            return user
        return None