import os
from flask import Flask, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2 import Error
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

app = Flask(__name__)

# Enable CORS for all routes (allows frontend to make requests)
CORS(app)

# Database configuration from environment variables
DB_CONFIG = {
    'host': os.environ.get('DB_HOSTNAME', 'localhost'),
    'port': os.environ.get('DB_PORT', '5432'),
    'database': os.environ.get('POSTGRES_DB', 'webapp_db'),
    'user': os.environ.get('POSTGRES_USER', 'webapp_user'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'supersecretpassword')
}

def get_db_connection():
    """Create and return a database connection."""
    try:
        connection = psycopg2.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return None

@app.route('/api/hello')
def hello():
    """Simple hello endpoint with environment-specific greeting."""
    message = os.environ.get('GREETING_MESSAGE', 'Hello')
    return jsonify(message=f"{message}, from the backend!")

@app.route('/api/health')
def health_check():
    """Health check endpoint that verifies database connectivity."""
    try:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute("SELECT version();")
            db_version = cursor.fetchone()
            cursor.close()
            connection.close()
            return jsonify({
                'status': 'healthy',
                'message': 'Backend and database are operational',
                'database_version': db_version[0] if db_version else 'Unknown'
            }), 200
        else:
            return jsonify({
                'status': 'unhealthy',
                'message': 'Cannot connect to database'
            }), 503
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'message': f'Health check failed: {str(e)}'
        }), 503

@app.route('/api/data')
def get_data():
    """Example endpoint that fetches data from the database."""
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        # Example query - you might want to create a simple table first
        cursor.execute("""
            SELECT 
                'test_data' as name,
                CURRENT_TIMESTAMP as timestamp,
                'QA Environment' as environment
        """)
        
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if result:
            return jsonify({
                'data': {
                    'name': result[0],
                    'timestamp': result[1].isoformat() if result[1] else None,
                    'environment': result[2]
                }
            })
        else:
            return jsonify({'data': None})
            
    except Exception as e:
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500

if __name__ == '__main__':
    # For development only - use gunicorn for production
    app.run(host='0.0.0.0', port=5000, debug=True)
