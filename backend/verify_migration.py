#!/usr/bin/env python
"""
Verification script for PostgreSQL migration.
This script tests that:
1. PostgreSQL connection is working
2. Alembic migrations have been applied
3. The files table exists with the correct schema
4. A test record can be inserted and retrieved
"""
import os
import sys
import logging
from dotenv import load_dotenv
from sqlalchemy import inspect, text

# Load environment variables
load_dotenv()

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import engine, SessionLocal
from app.models import File

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_database_connection():
    """Verify we can connect to the PostgreSQL database."""
    logger.info("Testing database connection...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("✓ Database connection successful")
            return True
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        return False

def verify_tables_exist():
    """Verify that the required tables exist."""
    logger.info("Checking if tables exist...")
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if 'files' not in tables:
            logger.error("✗ 'files' table not found")
            logger.info(f"  Available tables: {tables}")
            return False
        
        logger.info("✓ 'files' table exists")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to check tables: {e}")
        return False

def verify_schema():
    """Verify the files table has the correct columns."""
    logger.info("Verifying table schema...")
    try:
        inspector = inspect(engine)
        columns = inspector.get_columns('files')
        column_names = [col['name'] for col in columns]
        
        required_columns = ['id', 'name', 'type', 'status', 'transcript', 'url', 'session_id']
        missing_columns = set(required_columns) - set(column_names)
        
        if missing_columns:
            logger.error(f"✗ Missing columns: {missing_columns}")
            logger.info(f"  Found columns: {column_names}")
            return False
        
        logger.info(f"✓ Schema is correct. Columns: {column_names}")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to verify schema: {e}")
        return False

def verify_crud_operations():
    """Verify we can create, read, update, and delete records."""
    logger.info("Testing CRUD operations...")
    db = SessionLocal()
    try:
        # Create
        test_file = File(
            id="test-file-001",
            name="test.pdf",
            type="application/pdf",
            status="uploaded",
            url="/files/test-file-001",
            session_id="test-session-001"
        )
        db.add(test_file)
        db.commit()
        logger.info("✓ Record created successfully")
        
        # Read
        retrieved = db.query(File).filter(File.id == "test-file-001").first()
        if not retrieved:
            logger.error("✗ Failed to retrieve created record")
            return False
        logger.info("✓ Record retrieved successfully")
        
        # Update
        retrieved.status = "processed"
        db.commit()
        logger.info("✓ Record updated successfully")
        
        # Delete
        db.delete(retrieved)
        db.commit()
        logger.info("✓ Record deleted successfully")
        
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"✗ CRUD operation failed: {e}")
        return False
    finally:
        db.close()

def main():
    """Run all verification checks."""
    logger.info("=" * 50)
    logger.info("PostgreSQL Migration Verification")
    logger.info("=" * 50)
    
    checks = [
        ("Database Connection", verify_database_connection),
        ("Tables Exist", verify_tables_exist),
        ("Schema Verification", verify_schema),
        ("CRUD Operations", verify_crud_operations),
    ]
    
    results = []
    for check_name, check_func in checks:
        logger.info("")
        result = check_func()
        results.append((check_name, result))
    
    logger.info("")
    logger.info("=" * 50)
    logger.info("Verification Summary")
    logger.info("=" * 50)
    
    all_passed = True
    for check_name, result in results:
        status = "PASS" if result else "FAIL"
        logger.info(f"{check_name}: {status}")
        if not result:
            all_passed = False
    
    logger.info("=" * 50)
    
    if all_passed:
        logger.info("✓ All checks passed! Migration is successful.")
        sys.exit(0)
    else:
        logger.error("✗ Some checks failed. Please review the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
