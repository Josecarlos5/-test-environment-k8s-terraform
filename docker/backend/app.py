from flask import Flask, jsonify, request
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Database connection configuration
def get_db_connection():
    """Create a database connection using environment variables"""
    try:
        connection = psycopg2.connect(
            host=os.environ.get('DB_HOSTNAME', 'localhost'),
            port=os.environ.get('DB_PORT', '5432'),
            database=os.environ.get('POSTGRES_DB', 'webapp_db'),
            user=os.environ.get('POSTGRES_USER', 'webapp_user'),
            password=os.environ.get('POSTGRES_PASSWORD', 'defaultpassword'),
            cursor_factory=RealDictCursor
        )
        return connection
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None

# Initialize database tables
def init_db():
    """Initialize database tables if they don't exist"""
    try:
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                # Create a simple users table for demonstration
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        email VARCHAR(100) UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Insert some sample data if table is empty
                cursor.execute("SELECT COUNT(*) FROM users")
                if cursor.fetchone()[0] == 0:
                    sample_users = [
                        ('Alice Johnson', 'alice@example.com'),
                        ('Bob Smith', 'bob@example.com'),
                        ('Charlie Brown', 'charlie@example.com')
                    ]
                    cursor.executemany(
                        "INSERT INTO users (name, email) VALUES (%s, %s)",
                        sample_users
                    )
                    logger.info("Sample data inserted")
                
                conn.commit()
                logger.info("Database initialized successfully")
            conn.close()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

# Routes
@app.route('/api/hello', methods=['GET'])
def hello():
    """Simple hello endpoint"""
    message = os.environ.get('GREETING_MESSAGE', 'Hello')
    environment = os.environ.get('ENVIRONMENT_NAME', 'development')
    
    return jsonify({
        'message': f"{message} from the backend!",
        'environment': environment,
        'timestamp': datetime.now().isoformat(),
        'status': 'success'
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for Kubernetes probes"""
    try:
        # Test database connection
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            conn.close()
            db_status = 'healthy'
        else:
            db_status = 'unhealthy'
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'
    
    status_code = 200 if db_status == 'healthy' else 503
    
    return jsonify({
        'status': 'healthy' if db_status == 'healthy' else 'unhealthy',
        'database': db_status,
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    }), status_code

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all users from the database"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name, email, created_at FROM users ORDER BY id")
            users = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'users': users,
            'count': len(users),
            'status': 'success'
        })
    
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return jsonify({'error': 'Failed to fetch users'}), 500

@app.route('/api/users', methods=['POST'])
def create_user():
    """Create a new user"""
    try:
        data = request.get_json()
        
        if not data or 'name' not in data or 'email' not in data:
            return jsonify({'error': 'Name and email are required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id, name, email, created_at",
                (data['name'], data['email'])
            )
            new_user = cursor.fetchone()
            conn.commit()
        
        conn.close()
        
        return jsonify({
            'user': new_user,
            'status': 'created'
        }), 201
    
    except psycopg2.IntegrityError:
        return jsonify({'error': 'Email already exists'}), 409
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return jsonify({'error': 'Failed to create user'}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user by ID"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE id = %s RETURNING id", (user_id,))
            deleted_user = cursor.fetchone()
            conn.commit()
        
        conn.close()
        
        if deleted_user:
            return jsonify({
                'message': f'User {user_id} deleted successfully',
                'status': 'deleted'
            })
        else:
            return jsonify({'error': 'User not found'}), 404
    
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return jsonify({'error': 'Failed to delete user'}), 500

@app.route('/api/info', methods=['GET'])
def app_info():
    """Get application information"""
    return jsonify({
        'app_name': 'Test Environment Backend API',
        'version': '1.0.0',
        'python_version': os.sys.version,
        'environment': os.environ.get('ENVIRONMENT_NAME', 'development'),
        'database_host': os.environ.get('DB_HOSTNAME', 'localhost'),
        'greeting_message': os.environ.get('GREETING_MESSAGE', 'Hello'),
        'endpoints': [
            '/api/hello',
            '/api/health', 
            '/api/users',
            '/api/info'
        ]
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Initialize database when the app starts
    init_db()
    
    # Get configuration from environment variables
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting Flask app on {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Environment: {os.environ.get('ENVIRONMENT_NAME', 'development')}")
    
    # Run the Flask application
    app.run(host=host, port=port, debug=debug)

