#!/bin/bash

# Test script for the Dzinza Family Tree backend APIs

# 1. Register a New User
curl -X POST http://localhost:8090/api/register \
-H "Content-Type: application/json" \
-d '{
  "username": "testuser",
  "email": "testuser@example.com",
  "password": "StrongPassword123!",
  "full_name": "Test User"
}'

# 2. Login
curl -X POST http://localhost:8090/api/login \
-H "Content-Type: application/json" \
-c cookies.txt \
-d '{
  "username": "testuser",
  "password": "StrongPassword123!"
}'

# 3. Check Session Status
curl -X GET http://localhost:8090/api/session \
-H "Content-Type: application/json" \
-b cookies.txt

# 4. Logout
curl -X POST http://localhost:8090/api/logout \
-H "Content-Type: application/json" \
-b cookies.txt

# 5. Request Password Reset
curl -X POST http://localhost:8090/api/request-password-reset \
-H "Content-Type: application/json" \
-d '{
  "email": "testuser@example.com"
}'

# 6. Reset Password
curl -X POST http://localhost:8090/api/reset-password/<TOKEN> \
-H "Content-Type: application/json" \
-d '{
  "new_password": "NewStrongPassword123!"
}'

# 7. Create a New Tree
curl -X POST http://localhost:8090/api/trees \
-H "Content-Type: application/json" \
-b cookies.txt \
-d '{
  "name": "My Family Tree",
  "description": "A test family tree",
  "is_public": true
}'

# 8. Get All Trees for the User
curl -X GET http://localhost:8090/api/trees \
-H "Content-Type: application/json" \
-b cookies.txt

# 9. Set Active Tree
curl -X PUT http://localhost:8090/api/session/active_tree \
-H "Content-Type: application/json" \
-b cookies.txt \
-d '{
  "tree_id": "<TREE_ID>"
}'

# 10. Get All People in the Active Tree
curl -X GET http://localhost:8090/api/people \
-H "Content-Type: application/json" \
-b cookies.txt

# 11. Get a Specific Person
curl -X GET http://localhost:8090/api/people/<PERSON_ID> \
-H "Content-Type: application/json" \
-b cookies.txt

# 12. Create a New Person
curl -X POST http://localhost:8090/api/people \
-H "Content-Type: application/json" \
-b cookies.txt \
-d '{
  "first_name": "John",
  "last_name": "Doe",
  "gender": "male",
  "birth_date": "1980-01-01",
  "is_living": true
}'

# 13. Update a Person
curl -X PUT http://localhost:8090/api/people/<PERSON_ID> \
-H "Content-Type: application/json" \
-b cookies.txt \
-d '{
  "first_name": "John",
  "last_name": "Smith",
  "birth_date": "1980-02-01"
}'

# 14. Delete a Person
curl -X DELETE http://localhost:8090/api/people/<PERSON_ID> \
-H "Content-Type: application/json" \
-b cookies.txt

# 15. Get All Relationships in the Active Tree
curl -X GET http://localhost:8090/api/relationships \
-H "Content-Type: application/json" \
-b cookies.txt

# 16. Get a Specific Relationship
curl -X GET http://localhost:8090/api/relationships/<RELATIONSHIP_ID> \
-H "Content-Type: application/json" \
-b cookies.txt

# 17. Create a New Relationship
curl -X POST http://localhost:8090/api/relationships \
-H "Content-Type: application/json" \
-b cookies.txt \
-d '{
  "person1": "<PERSON1_ID>",
  "person2": "<PERSON2_ID>",
  "relationshipType": "sibling_full"
}'

# 18. Update a Relationship
curl -X PUT http://localhost:8090/api/relationships/<RELATIONSHIP_ID> \
-H "Content-Type: application/json" \
-b cookies.txt \
-d '{
  "relationshipType": "sibling_half"
}'

# 19. Delete a Relationship
curl -X DELETE http://localhost:8090/api/relationships/<RELATIONSHIP_ID> \
-H "Content-Type: application/json" \
-b cookies.txt

# 20. Get Tree Data for Visualization
curl -X GET http://localhost:8090/api/tree_data \
-H "Content-Type: application/json" \
-b cookies.txt

# 21. Perform Health Check
curl -X GET http://localhost:8090/health -H "Content-Type: application/json"