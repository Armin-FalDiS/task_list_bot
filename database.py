import os
import logging
import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Optional
from urllib.parse import urlparse, unquote

logger = logging.getLogger(__name__)

connection_pool: Optional[pool.ThreadedConnectionPool] = None

def get_connection_params():
    """Get database connection parameters from DATABASE_URL"""
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    
    parsed = urlparse(database_url)
    
    if not parsed.hostname:
        raise ValueError("Invalid DATABASE_URL: missing hostname")
    
    if not parsed.path or not parsed.path.lstrip('/'):
        raise ValueError("Invalid DATABASE_URL: missing database name")
    
    return {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'database': unquote(parsed.path.lstrip('/')),
        'user': unquote(parsed.username) if parsed.username else None,
        'password': unquote(parsed.password) if parsed.password else ''
    }

def init_connection_pool():
    global connection_pool
    
    if connection_pool is not None:
        return
    
    try:
        params = get_connection_params()
        
        if not params['user']:
            raise ValueError("Database username is required in DATABASE_URL")
        
        connection_pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            host=params['host'],
            port=params['port'],
            database=params['database'],
            user=params['user'],
            password=params['password']
        )
        
        logger.info("✅ PostgreSQL connection pool initialized")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize PostgreSQL connection pool: {e}")
        raise

@contextmanager
def get_db_connection():
    if connection_pool is None:
        init_connection_pool()
    
    conn = None
    try:
        conn = connection_pool.getconn()
        yield conn
    except psycopg2.Error as e:
        logger.error(f"❌ Database error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            connection_pool.putconn(conn)

@contextmanager
def get_db_cursor():
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            cursor.close()

def close_connection_pool():
    global connection_pool
    if connection_pool:
        connection_pool.closeall()
        connection_pool = None
        logger.info("🔌 PostgreSQL connection pool closed")
