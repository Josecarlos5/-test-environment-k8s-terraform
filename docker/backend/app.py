from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/api/hello')
def hello():
    message = os.environ.get('GREETING_MESSAGE', 'Hello')
    return jsonify(message=f"{message}, from the backend!")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) # listen on all interfaces inside the container
