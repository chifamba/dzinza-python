#!/bin/bash

#### Test script for the Dzinza Family Tree backend APIs

###Check that the backend is running
# 1. Health Check
curl -X GET http://localhost:8090/health -H "Content-Type: application/json"

### Let's check Admin User workflows
# Login as Admin User
curl -X POST http://localhost:8090/api/login -H "Content-Type: application/json" -c cookies.txt -d '{  "username": "admin","password": "01Admin_2025"}'

