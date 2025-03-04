from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/api/hello', methods=['GET'])
def hello():
    return jsonify({"message": "Hello, world!"})

if __name__ == '__main__':
    print("Starting test server on http://localhost:5001")
    app.run(debug=True, host='0.0.0.0', port=5001)