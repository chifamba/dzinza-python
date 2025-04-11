class User:
    def __init__(self, user_id, email, password):
        """
        Initializes a User object.

        Args:
            user_id (int): The unique identifier for the user.
            email (str): The email address of the user.
            password (str): The password of the user.
        """
        self.user_id = user_id
        self.email = email
        self.password = password
        self.trust_level = 1
        self.role = 'basic'  # Default role
        self.family_group_spaces = []

    def increase_trust_level(self):
        """
        Increases the trust level of the user by 1.
        Raises:
            ValueError: If the trust level is already at the maximum (5).
        """
        if self.trust_level >= 5:
            raise ValueError("Trust level is already at maximum (5)")
        self.trust_level += 1

    def decrease_trust_level(self):
        """
        Decreases the trust level of the user by 1.
        Raises:
            ValueError: If the trust level is already at the minimum (1).
        """
        if self.trust_level <= 1:
            raise ValueError("Trust level is already at minimum (1)")
        self.trust_level -= 1

    def set_role(self, role):
        """
        Sets the role of the user.

        Args:
            role (str): The role to set (basic, trusted, administrator, family_historian).

        Raises:
            ValueError: If the role is not valid.
        """
        valid_roles = ['basic', 'trusted', 'administrator', 'family_historian']
        if role not in valid_roles:
            raise ValueError(f"Invalid role: {role}. Valid roles are: {valid_roles}")
        self.role = role
    
    def add_family_group(self, family_group_id):
        """
        Adds a family group to the user's family group spaces.

        Args:
            family_group_id (int): The ID of the family group to add.

        Raises:
            ValueError: If the family group is already in the list.
        """
        if family_group_id in self.family_group_spaces:
            raise ValueError(f"Family group {family_group_id} is already in the user's family group spaces.")
        self.family_group_spaces.append(family_group_id)

    def remove_family_group(self, family_group_id):
        """
        Removes a family group from the user's family group spaces.

        Args:
            family_group_id (int): The ID of the family group to remove.

        Raises:
            ValueError: If the family group is not in the list.
        """
        if family_group_id not in self.family_group_spaces:
            raise ValueError(f"Family group {family_group_id} is not in the user's family group spaces.")
        self.family_group_spaces.remove(family_group_id)
