class User:
    def __init__(self, user_id, email, password):
        self.user_id = user_id
        self.email = email
        self.password = password
        self.trust_level = 1

    def increase_trust_level(self):
        """Increases the trust level of the user by 1.
        Raises ValueError if the trust level is already at the maximum (5).
        """
        if self.trust_level >= 5:
            raise ValueError("Trust level is already at maximum (5)")
        self.trust_level += 1

    def decrease_trust_level(self):
        """Decreases the trust level of the user by 1.
        Raises ValueError if the trust level is already at the minimum (1).
        """
        if self.trust_level <= 1:
            raise ValueError("Trust level is already at minimum (1)")
        self.trust_level -= 1
