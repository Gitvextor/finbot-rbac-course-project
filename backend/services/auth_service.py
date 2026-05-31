"""
Authentication service for Secure Corporate RAG Assistant
User registration, login, and session management
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from database import get_db
from models import User, UserLevel, Department, AuditLog, AuditAction


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class AuthService:
    """Authentication service"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """Decode and verify JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password"""
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return None
        if not AuthService.verify_password(password, user.password_hash):
            return None
        if not user.is_active:
            return None
        return user
    
    @staticmethod
    def register_user(
        db: Session,
        username: str,
        email: str,
        password: str,
        level: str = UserLevel.L4_STAFF.value,
        department: str = Department.PUBLIC.value,
        is_admin: bool = False
    ) -> Tuple[User, str]:
        """
        Register new user
        
        Returns:
            Tuple of (user, access_token)
        """
        # Check if username or email already exists
        if db.query(User).filter(User.username == username).first():
            raise ValueError("Username already registered")
        if db.query(User).filter(User.email == email).first():
            raise ValueError("Email already registered")
        
        # Create user
        user = User(
            username=username,
            email=email,
            password_hash=AuthService.hash_password(password),
            level=level,
            department=department,
            is_admin=is_admin
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Create access token
        access_token = AuthService.create_access_token(
            data={
                "sub": user.username,
                "user_id": user.id,
                "level": user.level,
                "department": user.department
            }
        )
        
        # Log registration
        audit_log = AuditLog(
            user_id=user.id,
            username=user.username,
            action=AuditAction.USER_CREATE.value,
            details=f"User {username} registered with level {level}, department {department}"
        )
        db.add(audit_log)
        db.commit()
        
        return user, access_token
    
    @staticmethod
    def login(
        db: Session,
        username: str,
        password: str,
        ip_address: str = None
    ) -> Tuple[User, str, bool]:
        """
        Login user
        
        Returns:
            Tuple of (user, access_token, is_new_token)
        """
        user = AuthService.authenticate_user(db, username, password)
        
        if user:
            # Update last login
            user.last_login = datetime.utcnow()
            db.commit()
            
            # Create token
            access_token = AuthService.create_access_token(
                data={
                    "sub": user.username,
                    "user_id": user.id,
                    "level": user.level,
                    "department": user.department
                }
            )
            
            # Log successful login
            audit_log = AuditLog(
                user_id=user.id,
                username=user.username,
                action=AuditAction.LOGIN.value,
                ip_address=ip_address
            )
            db.add(audit_log)
            db.commit()
            
            return user, access_token, True
        
        # Failed login attempt
        audit_log = AuditLog(
            username=username,
            action=AuditAction.LOGIN_FAILED.value,
            ip_address=ip_address,
            success=0,
            error_message="Invalid username or password"
        )
        db.add(audit_log)
        db.commit()
        
        return None, None, False
    
    @staticmethod
    def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
    ) -> User:
        """Get current user from token"""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        payload = AuthService.decode_token(token)
        if payload is None:
            raise credentials_exception
        
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise credentials_exception
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated"
            )
        
        return user


def get_current_active_user(current_user: User = Depends(AuthService.get_current_user)) -> User:
    """Dependency for getting current active user"""
    return current_user


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Dependency for requiring admin privileges"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


# Export get_current_user as module-level function for backward compatibility
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from token (standalone function)"""
    return AuthService.get_current_user(token, db)
