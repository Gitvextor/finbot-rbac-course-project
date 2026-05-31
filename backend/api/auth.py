"""
Authentication API routes for Secure Corporate RAG Assistant
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_db
from services import AuthService, get_current_active_user
from models import User
from .models import UserCreate, UserLogin, Token, UserResponse


router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        user, token = AuthService.register_user(
            db=db,
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            level=user_data.level,
            department=user_data.department,
            is_admin=user_data.is_admin
        )
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login with username and password"""
    # Get client IP
    client_ip = request.client.host if request.client else None
    
    user, token, success = AuthService.login(
        db=db,
        username=form_data.username,
        password=form_data.password,
        ip_address=client_ip
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {"access_token": token, "token_type": "bearer"}


@router.post("/login/json", response_model=Token)
def login_json(
    request: Request,
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """Login with JSON body"""
    client_ip = request.client.host if request.client else None
    
    user, token, success = AuthService.login(
        db=db,
        username=credentials.username,
        password=credentials.password,
        ip_address=client_ip
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user


@router.post("/logout")
def logout(current_user: User = Depends(get_current_active_user)):
    """Logout (client should discard token)"""
    return {"message": "Successfully logged out"}
