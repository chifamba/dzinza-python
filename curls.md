### A list of all the curl command needed to execute various backend requests ###

curl -X POST  http://localhost:8090/api/login -H 'Content-Type: application/json' -d '{"username": "admin", "password": "01Admin_2025"}' -c cookies.txt

curl -v -X GET http://localhost:8090/api/trees -H 'Content-Type: application/json' -b cookies.txt

 curl -X PUT http://localhost:8090/api/session/active_tree -H 'Content-Type: application/json' -d '{"tree_id": "7420e01d-73a7-4ee8-96a8-db6854b7beae"}' -b cookies.txt


curl -X GET http://localhost:8090/api/tree_data -H 'Content-Type: application/json'  -b cookies.txt

curl -X PUT http://localhost:8090/api/trees/active -H 'Content-Type: application/json' -d '{"tree_id": "7420e01d-73a7-4ee8-96a8-db6854b7beae"}' -b cookies.txt


curl -X GET http://localhost:8090/api/trees/{active_tree_id}  -H 'Content-Type: application/json' -b cookies.txt


curl -X GET http://localhost:8090/api/trees/{active_tree_id}/nodes -H 'Content-Type: application/json' -b cookies.txt


curl -X GET http://localhost:8090/api/trees/{active_tree_id}/edges -H 'Content-Type: application/json' -b cookies.txt


curl -X GET http://localhost:8090/api/trees/7420e01d-73a7-4ee8-96a8-db6854b7beae -H 'Content-Type: application/json' -b cookies.txt