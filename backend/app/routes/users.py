from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database.models import User, get_db
from app.database.schemas import UserCreate, UserUpdate, UserResponse, UserLogin, LoginResponse, Token
from app.utils.security import hash_password, verify_password, create_access_token
from app.utils.auth import get_current_user
from datetime import timedelta
import re

router = APIRouter(prefix="/api/users", tags=["Users"])


def validate_password(password: str):
    """Validate password strength"""
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")


@router.get("", response_model=List[UserResponse])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all users (requires authentication)"""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return users


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info"""
    return current_user


@router.get("/{uid}", response_model=UserResponse)
def get_user(
    uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific user (requires authentication)"""
    user = db.query(User).filter(User.uid == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user (public endpoint)"""
    # Validate password
    validate_password(user.password)
    
    # Check if username exists
    existing_username = db.query(User).filter(User.username == user.username).first()
    if existing_username:
        raise HTTPException(status_code=409, detail="User with this username already exists")
    
    # Check if email exists
    existing_email = db.query(User).filter(User.email == user.email).first()
    if existing_email:
        raise HTTPException(status_code=409, detail="User with this email already exists")
    
    # Hash password
    hashed_password = hash_password(user.password)
    
    # Create user
    db_user = User(
        username=user.username,
        email=user.email,
        password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.put("/{uid}", response_model=UserResponse)
def update_user(
    uid: str,
    user: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a user (requires authentication, can only update own profile)"""
    # Check if user is updating their own profile
    if current_user.uid != uid:
        raise HTTPException(status_code=403, detail="You can only update your own profile")
    
    db_user = db.query(User).filter(User.uid == uid).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check username uniqueness if updating
    if user.username and user.username != db_user.username:
        existing = db.query(User).filter(User.username == user.username).first()
        if existing:
            raise HTTPException(status_code=409, detail="User with this username already exists")
    
    # Check email uniqueness if updating
    if user.email and user.email != db_user.email:
        existing = db.query(User).filter(User.email == user.email).first()
        if existing:
            raise HTTPException(status_code=409, detail="User with this email already exists")
    
    # Validate and hash password if updating
    if user.password:
        validate_password(user.password)
        user.password = hash_password(user.password)
    
    # Update fields
    update_data = user.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user


@router.delete("/{uid}")
def delete_user(
    uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a user (requires authentication, can only delete own account)"""
    # Check if user is deleting their own account
    if current_user.uid != uid:
        raise HTTPException(status_code=403, detail="You can only delete your own account")
    
    db_user = db.query(User).filter(User.uid == uid).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted successfully"}


@router.post("/login", response_model=LoginResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """User login (public endpoint)"""
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(credentials.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.uid},
        expires_delta=timedelta(minutes=30)
    )
    
    return {
        "message": "Login successful",
        "user": UserResponse.model_validate(user),
        "token": {
            "access_token": access_token,
            "token_type": "bearer"
        }
    }
