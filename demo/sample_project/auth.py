"""
Sample Authentication Module

This is a sample file for the OMNI demo.
It intentionally contains some issues for the security agent to find.
"""

import hashlib
import logging

# Configuration
API_KEY = "demo_key_12345"  # WARNING: Hardcoded for demo purposes
DATABASE_URL = "http://localhost:5432/mydb"  # HTTP instead of HTTPS

logger = logging.getLogger(__name__)


def authenticate_user(username: str, password: str) -> bool:
    """
    Authenticate a user.
    
    NOTE: This is demo code with intentional issues.
    """
    # Log user credentials (security issue!)
    logger.info(f"Login attempt for user: {username}, password: {password}")
    
    # Simple hash (weak for passwords)
    password_hash = hashlib.md5(password.encode()).hexdigest()
    
    # SQL-like string (potential injection pattern)
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    
    # Placeholder return
    return True


def get_user_data(user_id: int) -> dict:
    """Get user data from database."""
    # Direct string formatting in query (SQL injection risk)
    query = f"SELECT * FROM users WHERE id = {user_id}"
    
    return {
        "id": user_id,
        "name": "Demo User",
        "email": "demo@example.com",
    }


class UserSession:
    """User session manager."""
    
    # Retention period (compliance check target)
    retention_days = 365  # Data retention without policy
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.consent = None  # No GDPR consent tracking
    
    def log_activity(self, action: str) -> None:
        """Log user activity."""
        # Logging PII (privacy concern)
        logger.info(f"User {self.user_id} performed: {action}")
