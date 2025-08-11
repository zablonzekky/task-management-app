from fastapi import FastAPI, APIRouter, HTTPException, Depends

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to my API!"}




ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: EmailStr
    full_name: str
    role: str = "user"  # "admin" or "user"
    hashed_password: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    password: str
    role: str = "user"

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    assigned_to: str  # user_id
    assigned_by: str  # admin_id
    status: str = "pending"  # "pending", "in_progress", "completed"
    deadline: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class TaskCreate(BaseModel):
    title: str
    description: str
    assigned_to: str
    deadline: datetime

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    status: Optional[str] = None
    deadline: Optional[datetime] = None

class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    assigned_to: str
    assigned_by: str
    assigned_to_user: Optional[UserResponse] = None
    assigned_by_user: Optional[UserResponse] = None
    status: str
    deadline: datetime
    created_at: datetime
    updated_at: datetime

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = await db.users.find_one({"id": user_id})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return User(**user)

async def get_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# Auth endpoints
@api_router.post("/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"$or": [{"username": user_data.username}, {"email": user_data.email}]})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    # Hash password
    hashed_password = get_password_hash(user_data.password)
    
    # Create user
    user_dict = user_data.dict()
    user_dict.pop("password")
    user_dict["hashed_password"] = hashed_password
    
    user = User(**user_dict)
    await db.users.insert_one(user.dict())
    
    return UserResponse(**user.dict())

@api_router.post("/auth/login", response_model=Token)
async def login(login_data: LoginRequest):
    user = await db.users.find_one({"username": login_data.username})
    if not user or not verify_password(login_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user["is_active"]:
        raise HTTPException(status_code=401, detail="User is inactive")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["id"]}, expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(**user)
    )

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(**current_user.dict())

# User management endpoints (Admin only)
@api_router.get("/users", response_model=List[UserResponse])
async def get_users(current_user: User = Depends(get_admin_user)):
    users = await db.users.find().to_list(1000)
    return [UserResponse(**user) for user in users]

@api_router.post("/users", response_model=UserResponse)
async def create_user(user_data: UserCreate, current_user: User = Depends(get_admin_user)):
    # Check if user exists
    existing_user = await db.users.find_one({"$or": [{"username": user_data.username}, {"email": user_data.email}]})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    # Hash password
    hashed_password = get_password_hash(user_data.password)
    
    # Create user
    user_dict = user_data.dict()
    user_dict.pop("password")
    user_dict["hashed_password"] = hashed_password
    
    user = User(**user_dict)
    await db.users.insert_one(user.dict())
    
    return UserResponse(**user.dict())

@api_router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, user_data: UserUpdate, current_user: User = Depends(get_admin_user)):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = {k: v for k, v in user_data.dict().items() if v is not None}
    if update_data:
        await db.users.update_one({"id": user_id}, {"$set": update_data})
        user.update(update_data)
    
    return UserResponse(**user)

@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: User = Depends(get_admin_user)):
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}

# Task management endpoints
@api_router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(current_user: User = Depends(get_current_user)):
    if current_user.role == "admin":
        # Admin can see all tasks
        tasks = await db.tasks.find().to_list(1000)
    else:
        # Users can only see their assigned tasks
        tasks = await db.tasks.find({"assigned_to": current_user.id}).to_list(1000)
    
    # Populate user information
    result = []
    for task in tasks:
        task_response = TaskResponse(**task)
        
        # Get assigned user info
        assigned_user = await db.users.find_one({"id": task["assigned_to"]})
        if assigned_user:
            task_response.assigned_to_user = UserResponse(**assigned_user)
        
        # Get assigning admin info
        assigned_by_user = await db.users.find_one({"id": task["assigned_by"]})
        if assigned_by_user:
            task_response.assigned_by_user = UserResponse(**assigned_by_user)
        
        result.append(task_response)
    
    return result

@api_router.post("/tasks", response_model=TaskResponse)
async def create_task(task_data: TaskCreate, current_user: User = Depends(get_admin_user)):
    # Verify assigned user exists
    assigned_user = await db.users.find_one({"id": task_data.assigned_to})
    if not assigned_user:
        raise HTTPException(status_code=404, detail="Assigned user not found")
    
    # Create task
    task_dict = task_data.dict()
    task_dict["assigned_by"] = current_user.id
    
    task = Task(**task_dict)
    await db.tasks.insert_one(task.dict())
    
    # Populate user information for response
    task_response = TaskResponse(**task.dict())
    task_response.assigned_to_user = UserResponse(**assigned_user)
    task_response.assigned_by_user = UserResponse(**current_user.dict())
    
    return task_response

@api_router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, task_data: TaskUpdate, current_user: User = Depends(get_current_user)):
    task = await db.tasks.find_one({"id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check permissions
    if current_user.role != "admin" and task["assigned_to"] != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Users can only update status, admins can update everything
    if current_user.role != "admin":
        # Regular users can only update status
        allowed_fields = {"status"}
        update_data = {k: v for k, v in task_data.dict().items() if v is not None and k in allowed_fields}
    else:
        # Admins can update everything except assigned_by
        update_data = {k: v for k, v in task_data.dict().items() if v is not None}
        if "assigned_to" in update_data:
            # Verify new assigned user exists
            assigned_user = await db.users.find_one({"id": update_data["assigned_to"]})
            if not assigned_user:
                raise HTTPException(status_code=404, detail="Assigned user not found")
    
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await db.tasks.update_one({"id": task_id}, {"$set": update_data})
        task.update(update_data)
    
    # Populate user information for response
    task_response = TaskResponse(**task)
    
    assigned_user = await db.users.find_one({"id": task["assigned_to"]})
    if assigned_user:
        task_response.assigned_to_user = UserResponse(**assigned_user)
    
    assigned_by_user = await db.users.find_one({"id": task["assigned_by"]})
    if assigned_by_user:
        task_response.assigned_by_user = UserResponse(**assigned_by_user)
    
    return task_response

@api_router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, current_user: User = Depends(get_admin_user)):
    result = await db.tasks.delete_one({"id": task_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully"}

# Dashboard stats
@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    if current_user.role == "admin":
        # Admin dashboard stats
        total_users = await db.users.count_documents({})
        total_tasks = await db.tasks.count_documents({})
        pending_tasks = await db.tasks.count_documents({"status": "pending"})
        in_progress_tasks = await db.tasks.count_documents({"status": "in_progress"})
        completed_tasks = await db.tasks.count_documents({"status": "completed"})
        
        return {
            "total_users": total_users,
            "total_tasks": total_tasks,
            "pending_tasks": pending_tasks,
            "in_progress_tasks": in_progress_tasks,
            "completed_tasks": completed_tasks
        }
    else:
        # User dashboard stats
        user_tasks = await db.tasks.count_documents({"assigned_to": current_user.id})
        user_pending = await db.tasks.count_documents({"assigned_to": current_user.id, "status": "pending"})
        user_in_progress = await db.tasks.count_documents({"assigned_to": current_user.id, "status": "in_progress"})
        user_completed = await db.tasks.count_documents({"assigned_to": current_user.id, "status": "completed"})
        
        return {
            "my_tasks": user_tasks,
            "pending_tasks": user_pending,
            "in_progress_tasks": user_in_progress,
            "completed_tasks": user_completed
        }

# Initialize admin user
async def create_admin_user():
    admin = await db.users.find_one({"role": "admin"})
    if not admin:
        admin_user = User(
            username="admin",
            email="admin@taskmanager.com",
            full_name="System Administrator",
            role="admin",
            hashed_password=get_password_hash("admin123")
        )
        await db.users.insert_one(admin_user.dict())
        print("Admin user created: username=admin, password=admin123")

@app.on_event("startup")
async def startup_event():
    await create_admin_user()

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
    
    
    from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# # Serve static files from React build
# app.mount("/static", StaticFiles(directory="static"), name="static")

# @app.get("/")
# async def serve_react_app():
#     return FileResponse(os.path.join("static", "index.html"))
