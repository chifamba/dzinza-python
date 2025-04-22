# API Documentation

This document describes the API endpoints for the Dzinza Family Tree Application.

## Authentication

### `/api/login` (POST)

-   **Description:** Authenticates a user and starts a session.
-   **Request Body:**
```
json
    {
        "username": "your_username",
        "password": "your_password"
    }
    
```
-   **Response Codes:**
    -   `200 OK`: Login successful.
    -   `400 Bad Request`: Missing username or password.
    -   `401 Unauthorized`: Invalid username or password.
    - `500 Internal Server Error`: An unexpected error occurred during login.
-   **Response Body (Success):**
```
json
    {
        "message": "Login successful!",
        "user": {
            "id": "user_id",
            "username": "user_name",
            "role": "user_role"
        }
    }
    
```
### `/api/register` (POST)

-   **Description:** Registers a new user.
-   **Request Body:**
```
json
    {
        "username": "new_username",
        "password": "new_password"
    }
    
```
-   **Response Codes:**
    -   `201 Created`: Registration successful.
    -   `400 Bad Request`: Missing username or password.
    -   `409 Conflict`: Username already exists.
    -   `500 Internal Server Error`: An unexpected error occurred during registration.
-   **Response Body (Success):**
```
json
    {
        "message": "Registration successful!",
        "user": {
            "id": "user_id",
            "username": "user_name",
            "role": "user_role"
        }
    }
    
```
### `/api/logout` (POST)

-   **Description:** Logs out the current user and clears the session.
-   **Authentication:** Required (user must be logged in).
-   **Request Body:** None
-   **Response Codes:**
    -   `200 OK`: Logout successful.
    -   `401 Unauthorized`: User not authenticated.
    - `500 Internal Server Error`: An unexpected error occurred during logout.
-   **Response Body (Success):**
```
json
    {
        "message": "Logout successful"
    }
    
```
### `/api/session` (GET)

-   **Description:** Retrieves the current session state.
-   **Authentication:** Not required.
- **Request Body:** None
-   **Response Codes:**
    -   `200 OK`: Session retrieved.
-   **Response Body (Authenticated):**
```
json
    {
        "isAuthenticated": true,
        "user": {
            "id": "user_id",
            "username": "user_name",
            "role": "user_role"
        }
    }
    
```
- **Response Body (Not Authenticated):**
```
json
    {
        "isAuthenticated": false,
        "user": null
    }
    
```
## People

### `/api/people` (GET)

-   **Description:** Retrieves all people in the family tree.
-   **Authentication:** Required.
- **Request Body:** None
-   **Response Codes:**
    -   `200 OK`: People retrieved.
    -   `401 Unauthorized`: User not authenticated.
    - `500 Internal Server Error`: Failed to retrieve people data.
-   **Response Body (Success):**
```
json
    [
        {
            "person_id": "person_id_1",
            "first_name": "John",
            "last_name": "Doe",
            "nickname": null,
            "birth_date": "1950-01-01",
            "death_date": null,
            "gender": "Male",
            "place_of_birth": "New York",
            "place_of_death": null,
            "notes": null,
        },
         {
            "person_id": "person_id_2",
            "first_name": "Jane",
            "last_name": "Doe",
            "nickname": null,
            "birth_date": "1955-03-15",
            "death_date": null,
            "gender": "Female",
            "place_of_birth": "Boston",
            "place_of_death": null,
            "notes": null,
        }
    ]
    
```
### `/api/people/{person_id}` (GET)

-   **Description:** Retrieves a specific person by their ID.
-   **Authentication:** Required.
-   **Request Parameters:**
    -   `person_id` (string): The ID of the person.
- **Request Body:** None
-   **Response Codes:**
    -   `200 OK`: Person retrieved.
    -   `401 Unauthorized`: User not authenticated.
    -   `404 Not Found`: Person not found.
     - `500 Internal Server Error`: Failed to retrieve person data.
-   **Response Body (Success):**
```
json
      {
            "person_id": "person_id_1",
            "first_name": "John",
            "last_name": "Doe",
            "nickname": null,
            "birth_date": "1950-01-01",
            "death_date": null,
            "gender": "Male",
            "place_of_birth": "New York",
            "place_of_death": null,
            "notes": null,
        }
    
```
### `/api/people` (POST)

-   **Description:** Adds a new person to the family tree.
-   **Authentication:** Required.
-   **Request Body:**
```
json
    {
        "first_name": "New",
        "last_name": "Person",
        "nickname": "NP",
        "birth_date": "2000-01-01",
        "death_date": null,
        "gender": "Other",
        "place_of_birth": "London",
        "place_of_death": null,
        "notes": "Some notes"
    }
    
```
-   **Response Codes:**
    -   `201 Created`: Person added.
    -   `400 Bad Request`: Invalid input data or missing fields.
    -   `401 Unauthorized`: User not authenticated.
     - `500 Internal Server Error`: An unexpected error occurred while adding person.
-   **Response Body (Success):**
```
json
    {
        "person_id": "newly_created_person_id",
        "first_name": "New",
        "last_name": "Person",
        "nickname": "NP",
        "birth_date": "2000-01-01",
        "death_date": null,
        "gender": "Other",
        "place_of_birth": "London",
        "place_of_death": null,
        "notes": "Some notes"
    }
    
```
### `/api/people/{person_id}` (PUT)

-   **Description:** Edits an existing person's details.
-   **Authentication:** Required.
-   **Request Parameters:**
    -   `person_id` (string): The ID of the person to edit.
-   **Request Body:**
```
json
    {
        "first_name": "Updated",
        "last_name": "Name"
    }
    
```
-   **Response Codes:**
    -   `200 OK`: Person updated.
    -   `400 Bad Request`: Invalid input data.
    -   `401 Unauthorized`: User not authenticated.
    -   `404 Not Found`: Person not found.
     - `500 Internal Server Error`: An unexpected error occurred while editing person.
-   **Response Body (Success):**
```
json
    {
         "person_id": "person_id",
        "first_name": "Updated",
        "last_name": "Name",
        "nickname": "NP",
        "birth_date": "2000-01-01",
        "death_date": null,
        "gender": "Other",
        "place_of_birth": "London",
        "place_of_death": null,
        "notes": "Some notes"
    }
    
```
### `/api/people/{person_id}` (DELETE)

-   **Description:** Deletes a person from the family tree.
-   **Authentication:** Required.
-   **Request Parameters:**
    -   `person_id` (string): The ID of the person to delete.
- **Request Body:** None
-   **Response Codes:**
    -   `204 No Content`: Person deleted.
    -   `401 Unauthorized`: User not authenticated.
    -   `404 Not Found`: Person not found.
    - `500 Internal Server Error`: An unexpected error occurred while deleting person.
-   **Response Body (Success):** Empty

## Relationships

### `/api/relationships` (GET)

-   **Description:** Retrieves all relationships in the family tree.
-   **Authentication:** Required.
- **Request Body:** None
-   **Response Codes:**
    -   `200 OK`: Relationships retrieved.
    -   `401 Unauthorized`: User not authenticated.
     - `500 Internal Server Error`: Failed to retrieve relationships data.
-   **Response Body (Success):**
```
json
    [
        {
            "relationship_id": "relationship_id_1",
            "person1_id": "person_id_1",
            "person2_id": "person_id_2",
            "rel_type": "Married",
             "attributes":{}
        },
         {
            "relationship_id": "relationship_id_2",
            "person1_id": "person_id_3",
            "person2_id": "person_id_4",
            "rel_type": "ParentChild",
            "attributes":{}
        }
    ]
    
```
### `/api/relationships` (POST)

-   **Description:** Adds a new relationship to the family tree.
-   **Authentication:** Required.
-   **Request Body:**
```
json
    {
        "person1_id": "person_id_1",
        "person2_id": "person_id_2",
        "rel_type": "Married"
    }
    
```
-   **Response Codes:**
    -   `201 Created`: Relationship added.
    -   `400 Bad Request`: Invalid input data or missing fields.
    -   `401 Unauthorized`: User not authenticated.
    - `500 Internal Server Error`: An unexpected error occurred while adding relationship.
-   **Response Body (Success):**
```
json
    {
         "relationship_id": "new_relationship_id",
            "person1_id": "person_id_1",
            "person2_id": "person_id_2",
            "rel_type": "Married",
            "attributes":{}
    }
    
```
### `/api/relationships/{relationship_id}` (PUT)

-   **Description:** Edits an existing relationship.
-   **Authentication:** Required.
-   **Request Parameters:**
    -   `relationship_id` (string): The ID of the relationship to edit.
-   **Request Body:**
```
json
    {
        "rel_type": "Divorced"
    }
    
```
-   **Response Codes:**
    -   `200 OK`: Relationship updated.
    -   `400 Bad Request`: Invalid input data.
    -   `401 Unauthorized`: User not authenticated.
    -   `404 Not Found`: Relationship not found.
     - `500 Internal Server Error`: An unexpected error occurred while editing relationship.
-   **Response Body (Success):**
```
json
    {
            "relationship_id": "relationship_id",
            "person1_id": "person_id_1",
            "person2_id": "person_id_2",
            "rel_type": "Divorced",
             "attributes":{}
    }
    
```
### `/api/relationships/{relationship_id}` (DELETE)

-   **Description:** Deletes a relationship from the family tree.
-   **Authentication:** Required.
-   **Request Parameters:**
    -   `relationship_id` (string): The ID of the relationship to delete.
- **Request Body:** None
-   **Response Codes:**
    -   `204 No Content`: Relationship deleted.
    -   `401 Unauthorized`: User not authenticated.
    -   `404 Not Found`: Relationship not found.
    - `500 Internal Server Error`: An unexpected error occurred while deleting relationship.
-   **Response Body (Success):** Empty

## Tree Data

### `/api/tree_data` (GET)

-   **Description:** Retrieves the data needed to visualize the family tree.
-   **Authentication:** Required.
- **Request Body:** None
-   **Response Codes:**
    -   `200 OK`: Tree data retrieved.
    -   `401 Unauthorized`: User not authenticated.
     - `500 Internal Server Error`: Failed to generate tree data.
-   **Response Body (Success):**