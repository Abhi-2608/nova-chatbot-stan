import sqlite3
import json
from typing import Optional, Any, List

DB_PATH = "chatbot.db"

def init_db():
    """Initialize the database with the user_profile table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            location TEXT,
            preferences TEXT,
            tone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_db():
    """Get a database connection."""
    return sqlite3.connect(DB_PATH)

def get_user_profile(user_id: str) -> dict:
    """
    Retrieve user profile from database.
    
    Args:
        user_id: Unique identifier for the user
        
    Returns:
        Dictionary containing user profile data
    """
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT name, location, preferences, tone FROM user_profile WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            return {}
        
        return {
            "name": row[0],
            "location": row[1],
            "preferences": json.loads(row[2]) if row[2] else [],
            "tone": row[3]
        }
    except json.JSONDecodeError:
        # Handle corrupted JSON data
        return {
            "name": row[0] if row else None,
            "location": row[1] if row else None,
            "preferences": [],
            "tone": row[3] if row else None
        }
    finally:
        conn.close()

def upsert_user_profile(user_id: str, field: str, value: Any) -> bool:
    """
    Insert or update a specific field in user profile.
    
    Args:
        user_id: Unique identifier for the user
        field: Field name to update (must be whitelisted)
        value: New value for the field
        
    Returns:
        True if successful, False otherwise
    """
    # Whitelist allowed fields to prevent SQL injection
    ALLOWED_FIELDS = {"name", "location", "preferences", "tone"}
    
    if field not in ALLOWED_FIELDS:
        raise ValueError(f"Field '{field}' is not allowed. Must be one of {ALLOWED_FIELDS}")
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Insert user if doesn't exist
        cursor.execute(
            "INSERT OR IGNORE INTO user_profile (user_id) VALUES (?)",
            (user_id,)
        )
        
        # Serialize preferences to JSON
        if field == "preferences":
            if not isinstance(value, (list, dict)):
                raise ValueError("Preferences must be a list or dict")
            value = json.dumps(value)
        
        # Use parameterized query with whitelist (safe from SQL injection)
        query = f"UPDATE user_profile SET {field} = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?"
        cursor.execute(query, (value, user_id))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error updating user profile: {e}")
        return False
    finally:
        conn.close()

def update_user_profile(user_id: str, updates: dict) -> bool:
    """
    Update multiple fields at once.
    
    Args:
        user_id: Unique identifier for the user
        updates: Dictionary of field-value pairs to update
        
    Returns:
        True if successful, False otherwise
    """
    ALLOWED_FIELDS = {"name", "location", "preferences", "tone"}
    
    # Validate all fields
    invalid_fields = set(updates.keys()) - ALLOWED_FIELDS
    if invalid_fields:
        raise ValueError(f"Invalid fields: {invalid_fields}")
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Insert user if doesn't exist
        cursor.execute(
            "INSERT OR IGNORE INTO user_profile (user_id) VALUES (?)",
            (user_id,)
        )
        
        # Build update query
        set_clauses = []
        values = []
        
        for field, value in updates.items():
            if field == "preferences":
                if not isinstance(value, (list, dict)):
                    raise ValueError("Preferences must be a list or dict")
                value = json.dumps(value)
            set_clauses.append(f"{field} = ?")
            values.append(value)
        
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        values.append(user_id)
        
        query = f"UPDATE user_profile SET {', '.join(set_clauses)} WHERE user_id = ?"
        cursor.execute(query, values)
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error updating user profile: {e}")
        return False
    finally:
        conn.close()

def delete_user_profile(user_id: str) -> bool:
    """
    Delete a user profile.
    
    Args:
        user_id: Unique identifier for the user
        
    Returns:
        True if successful, False otherwise
    """
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM user_profile WHERE user_id = ?", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error deleting user profile: {e}")
        return False
    finally:
        conn.close()

# Initialize database on import
init_db()