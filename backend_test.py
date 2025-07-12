#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Task Management System
Tests all authentication, user management, task management, and dashboard endpoints
"""

import requests
import json
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/frontend/.env')

# Get backend URL from environment
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'http://localhost:8001')
API_BASE = f"{BACKEND_URL}/api"

print(f"Testing backend at: {API_BASE}")

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        
    def log_pass(self, test_name):
        print(f"✅ PASS: {test_name}")
        self.passed += 1
        
    def log_fail(self, test_name, error):
        print(f"❌ FAIL: {test_name} - {error}")
        self.failed += 1
        self.errors.append(f"{test_name}: {error}")
        
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY: {self.passed}/{total} tests passed")
        print(f"{'='*60}")
        if self.errors:
            print("FAILURES:")
            for error in self.errors:
                print(f"  - {error}")
        return self.failed == 0

# Global test state
results = TestResults()
admin_token = None
user_token = None
test_user_id = None
test_task_id = None

def make_request(method, endpoint, data=None, token=None, expected_status=200):
    """Helper function to make API requests"""
    url = f"{API_BASE}{endpoint}"
    headers = {'Content-Type': 'application/json'}
    
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, json=data, headers=headers)
        elif method == 'PUT':
            response = requests.put(url, json=data, headers=headers)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
            
        if response.status_code != expected_status:
            return None, f"Expected status {expected_status}, got {response.status_code}: {response.text}"
            
        return response.json() if response.content else {}, None
        
    except requests.exceptions.RequestException as e:
        return None, f"Request failed: {str(e)}"
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON response: {str(e)}"

def test_admin_login():
    """Test admin login with default credentials"""
    global admin_token
    
    data = {
        "username": "admin",
        "password": "admin123"
    }
    
    response, error = make_request('POST', '/auth/login', data)
    if error:
        results.log_fail("Admin Login", error)
        return False
        
    if 'access_token' not in response:
        results.log_fail("Admin Login", "No access token in response")
        return False
        
    admin_token = response['access_token']
    
    # Verify user info
    if response.get('user', {}).get('role') != 'admin':
        results.log_fail("Admin Login", "User role is not admin")
        return False
        
    results.log_pass("Admin Login")
    return True

def test_user_registration():
    """Test user registration"""
    global test_user_id
    
    data = {
        "username": "testuser",
        "email": "testuser@example.com",
        "full_name": "Test User",
        "password": "testpass123",
        "role": "user"
    }
    
    response, error = make_request('POST', '/auth/register', data, expected_status=200)
    if error:
        results.log_fail("User Registration", error)
        return False
        
    if 'id' not in response:
        results.log_fail("User Registration", "No user ID in response")
        return False
        
    test_user_id = response['id']
    results.log_pass("User Registration")
    return True

def test_user_login():
    """Test user login"""
    global user_token
    
    data = {
        "username": "testuser",
        "password": "testpass123"
    }
    
    response, error = make_request('POST', '/auth/login', data)
    if error:
        results.log_fail("User Login", error)
        return False
        
    if 'access_token' not in response:
        results.log_fail("User Login", "No access token in response")
        return False
        
    user_token = response['access_token']
    
    # Verify user info
    if response.get('user', {}).get('role') != 'user':
        results.log_fail("User Login", "User role is not user")
        return False
        
    results.log_pass("User Login")
    return True

def test_auth_me_admin():
    """Test /auth/me endpoint with admin token"""
    if not admin_token:
        results.log_fail("Auth Me (Admin)", "No admin token available")
        return False
        
    response, error = make_request('GET', '/auth/me', token=admin_token)
    if error:
        results.log_fail("Auth Me (Admin)", error)
        return False
        
    if response.get('role') != 'admin':
        results.log_fail("Auth Me (Admin)", "Role is not admin")
        return False
        
    results.log_pass("Auth Me (Admin)")
    return True

def test_auth_me_user():
    """Test /auth/me endpoint with user token"""
    if not user_token:
        results.log_fail("Auth Me (User)", "No user token available")
        return False
        
    response, error = make_request('GET', '/auth/me', token=user_token)
    if error:
        results.log_fail("Auth Me (User)", error)
        return False
        
    if response.get('role') != 'user':
        results.log_fail("Auth Me (User)", "Role is not user")
        return False
        
    results.log_pass("Auth Me (User)")
    return True

def test_get_users_admin():
    """Test getting all users (admin only)"""
    if not admin_token:
        results.log_fail("Get Users (Admin)", "No admin token available")
        return False
        
    response, error = make_request('GET', '/users', token=admin_token)
    if error:
        results.log_fail("Get Users (Admin)", error)
        return False
        
    if not isinstance(response, list):
        results.log_fail("Get Users (Admin)", "Response is not a list")
        return False
        
    # Should have at least admin and test user
    if len(response) < 2:
        results.log_fail("Get Users (Admin)", f"Expected at least 2 users, got {len(response)}")
        return False
        
    results.log_pass("Get Users (Admin)")
    return True

def test_get_users_user_forbidden():
    """Test that regular users cannot access user list"""
    if not user_token:
        results.log_fail("Get Users (User Forbidden)", "No user token available")
        return False
        
    response, error = make_request('GET', '/users', token=user_token, expected_status=403)
    if error:
        results.log_fail("Get Users (User Forbidden)", error)
        return False
        
    results.log_pass("Get Users (User Forbidden)")
    return True

def test_create_user_admin():
    """Test creating a user as admin"""
    if not admin_token:
        results.log_fail("Create User (Admin)", "No admin token available")
        return False
        
    data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "full_name": "New User",
        "password": "newpass123",
        "role": "user"
    }
    
    response, error = make_request('POST', '/users', data, token=admin_token)
    if error:
        results.log_fail("Create User (Admin)", error)
        return False
        
    if 'id' not in response:
        results.log_fail("Create User (Admin)", "No user ID in response")
        return False
        
    results.log_pass("Create User (Admin)")
    return True

def test_update_user_admin():
    """Test updating a user as admin"""
    if not admin_token or not test_user_id:
        results.log_fail("Update User (Admin)", "Missing admin token or test user ID")
        return False
        
    data = {
        "full_name": "Updated Test User"
    }
    
    response, error = make_request('PUT', f'/users/{test_user_id}', data, token=admin_token)
    if error:
        results.log_fail("Update User (Admin)", error)
        return False
        
    if response.get('full_name') != "Updated Test User":
        results.log_fail("Update User (Admin)", "User not updated correctly")
        return False
        
    results.log_pass("Update User (Admin)")
    return True

def test_create_task_admin():
    """Test creating a task as admin"""
    global test_task_id
    
    if not admin_token or not test_user_id:
        results.log_fail("Create Task (Admin)", "Missing admin token or test user ID")
        return False
        
    # Create deadline 7 days from now
    deadline = (datetime.utcnow() + timedelta(days=7)).isoformat()
    
    data = {
        "title": "Test Task",
        "description": "This is a test task for API testing",
        "assigned_to": test_user_id,
        "deadline": deadline
    }
    
    response, error = make_request('POST', '/tasks', data, token=admin_token)
    if error:
        results.log_fail("Create Task (Admin)", error)
        return False
        
    if 'id' not in response:
        results.log_fail("Create Task (Admin)", "No task ID in response")
        return False
        
    test_task_id = response['id']
    
    # Verify task details
    if response.get('title') != "Test Task":
        results.log_fail("Create Task (Admin)", "Task title incorrect")
        return False
        
    if response.get('assigned_to') != test_user_id:
        results.log_fail("Create Task (Admin)", "Task assigned_to incorrect")
        return False
        
    results.log_pass("Create Task (Admin)")
    return True

def test_get_tasks_admin():
    """Test getting all tasks as admin"""
    if not admin_token:
        results.log_fail("Get Tasks (Admin)", "No admin token available")
        return False
        
    response, error = make_request('GET', '/tasks', token=admin_token)
    if error:
        results.log_fail("Get Tasks (Admin)", error)
        return False
        
    if not isinstance(response, list):
        results.log_fail("Get Tasks (Admin)", "Response is not a list")
        return False
        
    # Should have at least the test task
    if len(response) < 1:
        results.log_fail("Get Tasks (Admin)", "No tasks found")
        return False
        
    results.log_pass("Get Tasks (Admin)")
    return True

def test_get_tasks_user():
    """Test getting assigned tasks as user"""
    if not user_token:
        results.log_fail("Get Tasks (User)", "No user token available")
        return False
        
    response, error = make_request('GET', '/tasks', token=user_token)
    if error:
        results.log_fail("Get Tasks (User)", error)
        return False
        
    if not isinstance(response, list):
        results.log_fail("Get Tasks (User)", "Response is not a list")
        return False
        
    # Should have the assigned test task
    if len(response) < 1:
        results.log_fail("Get Tasks (User)", "No assigned tasks found")
        return False
        
    # Verify user can only see their assigned tasks
    for task in response:
        if task.get('assigned_to') != test_user_id:
            results.log_fail("Get Tasks (User)", "User can see tasks not assigned to them")
            return False
            
    results.log_pass("Get Tasks (User)")
    return True

def test_update_task_status_user():
    """Test updating task status as user"""
    if not user_token or not test_task_id:
        results.log_fail("Update Task Status (User)", "Missing user token or test task ID")
        return False
        
    data = {
        "status": "in_progress"
    }
    
    response, error = make_request('PUT', f'/tasks/{test_task_id}', data, token=user_token)
    if error:
        results.log_fail("Update Task Status (User)", error)
        return False
        
    if response.get('status') != "in_progress":
        results.log_fail("Update Task Status (User)", "Task status not updated")
        return False
        
    results.log_pass("Update Task Status (User)")
    return True

def test_update_task_admin():
    """Test updating task as admin"""
    if not admin_token or not test_task_id:
        results.log_fail("Update Task (Admin)", "Missing admin token or test task ID")
        return False
        
    data = {
        "title": "Updated Test Task",
        "status": "completed"
    }
    
    response, error = make_request('PUT', f'/tasks/{test_task_id}', data, token=admin_token)
    if error:
        results.log_fail("Update Task (Admin)", error)
        return False
        
    if response.get('title') != "Updated Test Task":
        results.log_fail("Update Task (Admin)", "Task title not updated")
        return False
        
    if response.get('status') != "completed":
        results.log_fail("Update Task (Admin)", "Task status not updated")
        return False
        
    results.log_pass("Update Task (Admin)")
    return True

def test_dashboard_stats_admin():
    """Test dashboard stats for admin"""
    if not admin_token:
        results.log_fail("Dashboard Stats (Admin)", "No admin token available")
        return False
        
    response, error = make_request('GET', '/dashboard/stats', token=admin_token)
    if error:
        results.log_fail("Dashboard Stats (Admin)", error)
        return False
        
    # Check required admin stats fields
    required_fields = ['total_users', 'total_tasks', 'pending_tasks', 'in_progress_tasks', 'completed_tasks']
    for field in required_fields:
        if field not in response:
            results.log_fail("Dashboard Stats (Admin)", f"Missing field: {field}")
            return False
        if not isinstance(response[field], int):
            results.log_fail("Dashboard Stats (Admin)", f"Field {field} is not an integer")
            return False
            
    results.log_pass("Dashboard Stats (Admin)")
    return True

def test_dashboard_stats_user():
    """Test dashboard stats for user"""
    if not user_token:
        results.log_fail("Dashboard Stats (User)", "No user token available")
        return False
        
    response, error = make_request('GET', '/dashboard/stats', token=user_token)
    if error:
        results.log_fail("Dashboard Stats (User)", error)
        return False
        
    # Check required user stats fields
    required_fields = ['my_tasks', 'pending_tasks', 'in_progress_tasks', 'completed_tasks']
    for field in required_fields:
        if field not in response:
            results.log_fail("Dashboard Stats (User)", f"Missing field: {field}")
            return False
        if not isinstance(response[field], int):
            results.log_fail("Dashboard Stats (User)", f"Field {field} is not an integer")
            return False
            
    results.log_pass("Dashboard Stats (User)")
    return True

def test_delete_task_admin():
    """Test deleting a task as admin"""
    if not admin_token or not test_task_id:
        results.log_fail("Delete Task (Admin)", "Missing admin token or test task ID")
        return False
        
    response, error = make_request('DELETE', f'/tasks/{test_task_id}', token=admin_token)
    if error:
        results.log_fail("Delete Task (Admin)", error)
        return False
        
    if 'message' not in response:
        results.log_fail("Delete Task (Admin)", "No success message in response")
        return False
        
    results.log_pass("Delete Task (Admin)")
    return True

def test_delete_user_admin():
    """Test deleting a user as admin"""
    if not admin_token or not test_user_id:
        results.log_fail("Delete User (Admin)", "Missing admin token or test user ID")
        return False
        
    response, error = make_request('DELETE', f'/users/{test_user_id}', token=admin_token)
    if error:
        results.log_fail("Delete User (Admin)", error)
        return False
        
    if 'message' not in response:
        results.log_fail("Delete User (Admin)", "No success message in response")
        return False
        
    results.log_pass("Delete User (Admin)")
    return True

def test_invalid_token():
    """Test API with invalid token"""
    response, error = make_request('GET', '/auth/me', token='invalid_token', expected_status=401)
    if error:
        results.log_fail("Invalid Token", error)
        return False
        
    results.log_pass("Invalid Token")
    return True

def run_all_tests():
    """Run all backend API tests"""
    print("Starting Backend API Tests...")
    print("="*60)
    
    # Authentication Tests
    print("\n🔐 AUTHENTICATION TESTS")
    test_admin_login()
    test_user_registration()
    test_user_login()
    test_auth_me_admin()
    test_auth_me_user()
    test_invalid_token()
    
    # User Management Tests
    print("\n👥 USER MANAGEMENT TESTS")
    test_get_users_admin()
    test_get_users_user_forbidden()
    test_create_user_admin()
    test_update_user_admin()
    
    # Task Management Tests
    print("\n📋 TASK MANAGEMENT TESTS")
    test_create_task_admin()
    test_get_tasks_admin()
    test_get_tasks_user()
    test_update_task_status_user()
    test_update_task_admin()
    
    # Dashboard Tests
    print("\n📊 DASHBOARD TESTS")
    test_dashboard_stats_admin()
    test_dashboard_stats_user()
    
    # Cleanup Tests
    print("\n🗑️ CLEANUP TESTS")
    test_delete_task_admin()
    test_delete_user_admin()
    
    # Print final results
    success = results.summary()
    return success

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)