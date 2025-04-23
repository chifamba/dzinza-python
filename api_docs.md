API DocumentationThis document describes the API endpoints for the Dzinza Family Tree Application. All endpoints requiring authentication expect session cookies to be sent (withCredentials: true in frontend axios calls).Base URL: /api (relative to the backend server address, e.g., http://localhost:8090/api)Authentication/login (POST)Description: Authenticates a user via username and password. Sets session cookies on success.Authentication: None required.Request Body:{
    "username": "your_username",
    "password": "your_password"
}
Response Codes:200 OK: Login successful.400 Bad Request: Missing username or password, or invalid JSON.401 Unauthorized: Invalid username or password.500 Internal Server Error: An unexpected error occurred during login.503 Service Unavailable: Authentication service not initialized.Response Body (Success - 200 OK):{
    "message": "Login successful!",
    "user": {
        "id": "user_uuid",
        "username": "user_name",
        "role": "user_role" // e.g., "basic", "admin"
    }
}
Response Body (Error - 400/401):{
    "error": "Bad Request/Unauthorized",
    "message": "Specific error message (e.g., Username and password are required / Invalid username or password.)"
}
/register (POST)Description: Registers a new user with a 'basic' role by default.Authentication: None required.Request Body:{
    "username": "new_username",
    "password": "new_password" // Min length/complexity might be enforced by backend logic (currently basic check)
}
Response Codes:201 Created: Registration successful.400 Bad Request: Missing username/password, empty values, or invalid JSON.409 Conflict: Username already exists.500 Internal Server Error: An unexpected error occurred during registration (e.g., hashing failed, save failed).503 Service Unavailable: Registration service not initialized.Response Body (Success - 201 Created):{
    "message": "Registration successful!",
    "user": {
        "id": "new_user_uuid",
        "username": "new_username",
        "role": "basic"
    }
}
Response Body (Error - 409 Conflict):{
    "error": "Username 'new_username' is already taken."
}
/logout (POST)Description: Logs out the current user and clears the server-side session.Authentication: Required.Request Body: None (Empty object {} might be needed depending on frontend library).Response Codes:200 OK: Logout successful.401 Unauthorized: User not authenticated.500 Internal Server Error: An unexpected error occurred during logout.503 Service Unavailable: Core components not initialized.Response Body (Success - 200 OK):{
    "message": "Logout successful"
}
/session (GET)Description: Retrieves the current authentication status and user information if logged in.Authentication: Not required.Request Body: None.Response Codes:200 OK: Session status retrieved.Response Body (Authenticated):{
    "isAuthenticated": true,
    "user": {
        "id": "user_uuid",
        "username": "user_name",
        "role": "user_role"
    }
}
Response Body (Not Authenticated):{
    "isAuthenticated": false,
    "user": null
}
Password Reset/request-password-reset (POST)Description: Initiates the password reset process by sending an email with a reset link to the user's registered email address (which is assumed to be their username in this implementation).Authentication: None required.Request Body:{
    "email": "user_email_or_username"
}
Response Codes:200 OK: Request processed (email sent if user exists, but response is generic to prevent enumeration).400 Bad Request: Missing or empty email field, or invalid JSON.500 Internal Server Error: Failed to generate token or send email.503 Service Unavailable: User manager or email service not available.Response Body (Success - 200 OK):{
    "message": "If an account exists for this email, a password reset link has been sent."
}
/reset-password/<token> (POST)Description: Resets the user's password using a valid, non-expired token received via email.Authentication: None required (token provides authorization).URL Parameters:token (string): The password reset token.Request Body:{
    "new_password": "new_secure_password" // Basic validation (min length 8) applied
}
Response Codes:200 OK: Password reset successful.400 Bad Request: Missing new password, invalid/expired token, or password validation failed (e.g., too short).500 Internal Server Error: Failed to hash password or save user data.503 Service Unavailable: User manager not available.Response Body (Success - 200 OK):{
    "message": "Password reset successfully."
}
Response Body (Error - 400 Bad Request):{
    "error": "Bad Request",
    "message": "Specific error message (e.g., Invalid or expired password reset token... / New password cannot be empty...)"
}
People/people (GET)Description: Retrieves all people in the family tree.Authentication: Required.Request Body: None.Response Codes:200 OK: People retrieved successfully.401 Unauthorized: User not authenticated.500 Internal Server Error: Failed to retrieve people data.503 Service Unavailable: Family tree service not available.Response Body (Success - 200 OK): An array of Person objects.[
    {
        "person_id": "uuid_string",
        "first_name": "John",
        "last_name": "Doe",
        "nickname": null,
        "birth_date": "1950-01-01", // YYYY-MM-DD or null
        "death_date": null,         // YYYY-MM-DD or null
        "gender": "Male",           // "Male", "Female", "Other", or null
        "place_of_birth": "New York", // String or null
        "place_of_death": null,       // String or null
        "notes": "Some notes about John.", // String or null
        "attributes": {}            // Custom attributes dictionary
    },
    // ... more person objects
]
/people/{person_id} (GET)Description: Retrieves a specific person by their ID.Authentication: Required.URL Parameters:person_id (string): The UUID of the person.Request Body: None.Response Codes:200 OK: Person retrieved successfully.401 Unauthorized: User not authenticated.404 Not Found: Person with the specified ID not found.500 Internal Server Error: Failed to retrieve person data.503 Service Unavailable: Family tree service not available.Response Body (Success - 200 OK): A single Person object (see format above)./people (POST)Description: Adds a new person to the family tree.Authentication: Required.Request Body: A Person object (without person_id). first_name is required.{
    "first_name": "New",
    "last_name": "Person", // Optional, defaults to ""
    "nickname": "NP",      // Optional
    "birth_date": "2000-01-01", // Optional, YYYY-MM-DD
    "death_date": null,         // Optional, YYYY-MM-DD
    "gender": "Other",          // Optional ("Male", "Female", "Other")
    "place_of_birth": "London", // Optional
    "place_of_death": null,       // Optional
    "notes": "Some notes",      // Optional
    "attributes": {"custom_key": "value"} // Optional
}
Response Codes:201 Created: Person added successfully.400 Bad Request: Invalid input data (e.g., missing first_name, invalid date format, DOD before DOB, invalid gender). Response body contains validation details: {"error": "Validation failed", "details": {"field_name": "error message"}}.401 Unauthorized: User not authenticated.500 Internal Server Error: An unexpected error occurred while adding the person.503 Service Unavailable: Family tree service not available.Response Body (Success - 201 Created): The newly created Person object (including the generated person_id)./people/{person_id} (PUT)Description: Edits an existing person's details. Only include fields to be updated.Authentication: Required.URL Parameters:person_id (string): The UUID of the person to edit.Request Body: An object containing the fields to update.{
    "last_name": "UpdatedName",
    "notes": "Updated notes.",
    "death_date": "2024-01-01"
    // Include any fields from the Person object to update
}
Response Codes:200 OK: Person updated successfully (even if no effective changes were made).400 Bad Request: Invalid input data (e.g., invalid date format, DOD before DOB, invalid gender). Response body contains validation details.401 Unauthorized: User not authenticated.404 Not Found: Person with the specified ID not found.500 Internal Server Error: An unexpected error occurred while editing the person.503 Service Unavailable: Family tree service not available.Response Body (Success - 200 OK): The updated Person object./people/{person_id} (DELETE)Description: Deletes a person and their associated relationships from the family tree.Authentication: Required.URL Parameters:person_id (string): The UUID of the person to delete.Request Body: None.Response Codes:204 No Content: Person deleted successfully.401 Unauthorized: User not authenticated.404 Not Found: Person with the specified ID not found.500 Internal Server Error: An unexpected error occurred while deleting the person.503 Service Unavailable: Family tree service not available.Response Body (Success - 204 No Content): Empty.Relationships/relationships (GET)Description: Retrieves all relationships in the family tree.Authentication: Required.Request Body: None.Response Codes:200 OK: Relationships retrieved successfully.401 Unauthorized: User not authenticated.500 Internal Server Error: Failed to retrieve relationships data.503 Service Unavailable: Family tree service not available.Response Body (Success - 200 OK): An array of Relationship objects.[
    {
        "rel_id": "uuid_string", // ID of the relationship itself
        "person1_id": "person_uuid_1",
        "person2_id": "person_uuid_2",
        "rel_type": "spouse", // e.g., "spouse", "parent", "child", "sibling"
        "attributes": {"start_date": "1980-05-20"} // Custom attributes
    },
    // ... more relationship objects
]
/relationships (POST)Description: Adds a new relationship between two people.Authentication: Required.Request Body:{
    "person1": "person_uuid_1", // ID of the first person
    "person2": "person_uuid_2", // ID of the second person
    "relationshipType": "parent", // Type of relationship (from person1 to person2)
    "attributes": {"custom": "data"} // Optional attributes dictionary
}
Response Codes:201 Created: Relationship added successfully.400 Bad Request: Invalid input data (e.g., missing IDs, invalid type, persons not found, self-relationship). Response body contains validation details.401 Unauthorized: User not authenticated.409 Conflict: Relationship might already exist (depends on backend logic).500 Internal Server Error: An unexpected error occurred while adding the relationship.503 Service Unavailable: Family tree service not available.Response Body (Success - 201 Created): The newly created Relationship object (including the generated rel_id)./relationships/{relationship_id} (PUT)Description: Edits an existing relationship's type or attributes. Can also change the persons involved.Authentication: Required.URL Parameters:relationship_id (string): The UUID of the relationship to edit.Request Body: An object containing the fields to update.{
    "relationshipType": "sibling", // Optional: Change the type
    "attributes": {"new_attr": "value"}, // Optional: Update/add attributes
    "person1": "new_person_uuid_1", // Optional: Change person 1
    "person2": "new_person_uuid_2"  // Optional: Change person 2
}
Response Codes:200 OK: Relationship updated successfully (even if no effective changes were made).400 Bad Request: Invalid input data (e.g., invalid type, invalid attributes format, persons not found if changed, self-relationship). Response body contains validation details.401 Unauthorized: User not authenticated.404 Not Found: Relationship with the specified ID not found.500 Internal Server Error: An unexpected error occurred while editing the relationship.503 Service Unavailable: Family tree service not available.Response Body (Success - 200 OK): The updated Relationship object./relationships/{relationship_id} (DELETE)Description: Deletes a relationship from the family tree.Authentication: Required.URL Parameters:relationship_id (string): The UUID of the relationship to delete.Request Body: None.Response Codes:204 No Content: Relationship deleted successfully.401 Unauthorized: User not authenticated.404 Not Found: Relationship with the specified ID not found.500 Internal Server Error: An unexpected error occurred while deleting the relationship.503 Service Unavailable: Family tree service not available.Response Body (Success - 204 No Content): Empty.Tree Data/tree_data (GET)Description: Retrieves node and link data formatted for use with visualization libraries like React Flow. Supports optional lazy loading via query parameters (currently returns full tree).Authentication: Required.Query Parameters (Optional):start_node (string): The person_id to start the tree traversal from. If omitted, the full tree is returned. (Note: Backend currently returns full tree regardless)depth (integer): The maximum depth to traverse from the start_node (0 = start node only). Ignored if start_node is omitted. (Note: Backend currently returns full tree regardless)Request Body: None.Response Codes:200 OK: Tree data retrieved successfully.400 Bad Request: Invalid depth parameter (e.g., not an integer, negative).401 Unauthorized: User not authenticated.500 Internal Server Error: Failed to generate tree data.503 Service Unavailable: Family tree service not available.Response Body (Success - 200 OK):{
    "nodes": [
        {
            "id": "person_uuid_1",
            "type": "personNode", // Node type for React Flow
            "data": {
                "id": "person_uuid_1", // Pass ID for editing
                "label": "John Doe (JD)", // Display name
                "full_name": "John Doe",
                "gender": "Male",
                "dob": "1950-01-01",
                "dod": null,
                "birth_place": "New York",
                "death_place": null,
                "photoUrl": null // Placeholder for photo URL
            },
            "position": {"x": 0, "y": 0} // Position will be calculated by layout algorithm
        },
        // ... more node objects
    ],
    "links": [ // Renamed from 'edges' in some contexts
        {
            "id": "relationship_uuid_1", // Relationship ID
            "source": "person_uuid_1", // Source node ID
            "target": "person_uuid_2", // Target node ID
            "type": "default", // Edge type for React Flow (e.g., 'default', 'smoothstep')
            "animated": false,
            "label": "spouse", // Label to display on the edge
            "data": {} // Optional relationship attributes
        },
        // ... more link/edge objects
    ]
}
Admin User Management/users (GET)Description: Retrieves a list of all registered users. (Admin only)Authentication: Required (Admin role).Request Body: None.Response Codes:200 OK: User list retrieved successfully.401 Unauthorized: User not authenticated.403 Forbidden: User is not an admin.500 Internal Server Error: Failed to retrieve user list.503 Service Unavailable: User manager not available.Response Body (Success - 200 OK): An array of User summary objects (excluding sensitive info like password hash, tokens).[
    {
        "user_id": "user_uuid_1",
        "username": "testuser",
        "role": "basic"
        // Other non-sensitive fields might be included if needed
    },
    {
        "user_id": "user_uuid_2",
        "username": "adminuser",
        "role": "admin"
    }
    // ... more user objects
]
/users/{user_id} (DELETE)Description: Deletes a specified user. (Admin only)Authentication: Required (Admin role).URL Parameters:user_id (string): The UUID of the user to delete.Request Body: None.Response Codes:204 No Content: User deleted successfully.401 Unauthorized: User not authenticated.403 Forbidden: User is not an admin or attempting self-deletion.404 Not Found: User with the specified ID not found.500 Internal Server Error: An unexpected error occurred while deleting the user.503 Service Unavailable: User manager not available.Response Body (Success - 204 No Content): Empty./users/{user_id}/role (PUT)Description: Changes the role of a specified user. (Admin only)Authentication: Required (Admin role).URL Parameters:user_id (string): The UUID of the user whose role is to be changed.Request Body:{
    "role": "admin" // The new role ("basic" or "admin")
}
Response Codes:200 OK: Role updated successfully (or no change needed).400 Bad Request: Missing role field or invalid role value provided.401 Unauthorized: User not authenticated.403 Forbidden: User is not an admin.404 Not Found: User with the specified ID not found.500 Internal Server Error: An unexpected error occurred while setting the role.503 Service Unavailable: User manager not available.Response Body (Success - 200 OK):{
    "user_id": "user_uuid",
    "username": "target_username",
    "role": "new_role" // The updated role
}
