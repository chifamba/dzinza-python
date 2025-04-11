from src.user import User
from src.audit_log import AuditLog
import datetime
from datetime import timedelta

class UserManager:
    def __init__(self, audit_log: AuditLog = None):
        self.users = {}
        self.audit_log = audit_log if audit_log else AuditLog()

    def create_user(self, user_id, email, password, acting_user_id="system"):
        if email in self.users or any(u.user_id == user_id for u in self.users.values()):
            raise ValueError("Email or user ID already in use")
        user = User(user_id, email, password, access_level='user')
        self.users[user.user_id] = user
        self.audit_log.log_event(
            user_id=acting_user_id,
            event_type="user_created",
            description=f"User with email {email} created"
        )
        return user

    def validate_user(self, email, password):
        user = next((u for u in self.users.values() if u.email == email), None)
        if user and user.password == password:

            return user
        return None

    def promote_to_trusted(self, user_id, acting_user_id="system"):
        previous_user = self.users.get(user_id)

        user = self.users.get(user_id)
        if not user:
            raise ValueError("User does not exist")
        if user.trust_level >= 2:
             raise ValueError("User is already a trusted user")
        user.increase_trust_level()

        self.audit_log.log_event(
            user_id=acting_user_id,
            event_type="user_updated",
            description=f"User with id {user_id} trust level updated from {previous_user.trust_level} to {user.trust_level}"
        )
    def promote_to_family_historian(self, user_id, acting_user_id="system"):
        user = self.users.get(user_id)
        previous_user = self.users.get(user_id)
        if not user:
            raise ValueError("User does not exist")
        if user.role == 'family_historian':
            raise ValueError("User is already a family historian")
        user.set_role('family_historian')
    
    def add_trust_points(self, user_id, points):
        previous_user = self.users.get(user_id)
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User does not exist")

        user.add_trust_points(points)
        self.audit_log.log_event(
            user_id=acting_user_id,
            event_type="user_updated",
            description=f"User with id {user_id} trust points updated from {previous_user.trust_points} to {user.trust_points}"
        )
    
    def apply_trust_decay(self):
        for user in self.users.values():
            if user.is_inactive():
                if user.trust_points >= 50:
                  user.remove_trust_points(50)

        user.add_trust_points(points)
    def demote_to_basic(self, user_id, acting_user_id="system"):
        previous_user = self.users.get(user_id)
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User does not exist")
        if user.role == 'basic':
            raise ValueError('User is already a basic user')
        user.set_role('basic')
        self.audit_log.log_event(
            user_id=acting_user_id,
            event_type="user_updated",
            description=f"User with id {user_id} role updated from {previous_user.role} to {user.role}"
        )
    
    def promote_to_administrator(self, user_id, acting_user_id="system"):
        previous_user = self.users.get(user_id)
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User does not exist")
        if user.access_level == 'administrator':
            raise ValueError("User is already an administrator")
        user.access_level = 'administrator'
        self.audit_log.log_event(
            user_id=acting_user_id,
            event_type="user_updated",
            description=f"User with id {user_id} access level updated from {previous_user.access_level} to {user.access_level}"
        )

    def delete_user(self, user_id, acting_user_id="system"):
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User does not exist.")
        del self.users[user_id]
        self.audit_log.log_event(
            user_id=acting_user_id,
            event_type="user_deleted",
            description=f"User with id {user_id} was deleted"
        )
        