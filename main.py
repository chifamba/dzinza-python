from src.user_management import UserManager  # Import the UserManager class
from src.user import User  # Import the User class

def main():
    # Create an instance of UserManager
    user_manager = UserManager()

    # Create a new user
    user_id = 1  # User ID must be an integer
    email = "test@example.com"  # Email must be a string
    password = "password123"  # Password must be a string
    user_manager.create_user(user_id, email, password)

if __name__ == '__main__':
    main()
