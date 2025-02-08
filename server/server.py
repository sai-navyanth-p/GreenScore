from flask import Flask, jsonify, request
from pymongo import MongoClient
from datetime import datetime, timedelta
import os
import requests
import ssl
import certifi
from dotenv import load_dotenv
from bson import ObjectId
import pytz

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# MongoDB Connection Setup
try:
    client = MongoClient(
        os.getenv("MONGODB_URI"),
        tls=True,
        tlsCAFile=certifi.where(),
        tlsAllowInvalidCertificates=True,
    )
    client.server_info()  # Test connection to MongoDB
    db = client.get_database('green')  # Specify database name
    print(f"Connected to database: {db.name}")
    
    # Initialize collections
    users = db['users']
    transactions = db['transactions']
    goals = db['goals']
    
    # Print document counts for each collection (for debugging)
    print(f"Users count: {users.count_documents({})}")
    print(f"Transactions count: {transactions.count_documents({})}")
    print(f"Goals count: {goals.count_documents({})}")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    exit(1)

# Helper Functions
def get_ai_response(prompt, data):
    """Get AI response using OpenAI API"""
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{
            "role": "user",
            "content": f"{prompt}\n\n{str(data)}"
        }]
    }
    
    try:
        # Call OpenAI API to get response
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=10
        )
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"OpenAI API Error: {str(e)}")
        return None

# Routes
@app.route("/api/account", methods=["GET"])
def get_account():
    """Fetch account details for a given user"""
    user_id = request.args.get("user_id")  # Get user_id from query parameters
    print(f"Fetching account for user: {user_id}")
    user = users.find_one({"user_id": user_id})
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "account_number": user.get("account_number"),
        "account_type": user.get("account_type"),
        "balance": user.get("balance", 0)
    })

@app.route("/api/green-score", methods=["GET"])
def get_green_score():
    """Fetch the green score of a user"""
    user_id = request.args.get("user_id")
    user = users.find_one({"user_id": user_id})
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "score": user.get("green_score", 0),
        "percentile": 75,  # Example value
        "monthly_comparison": 15  # Example value
    })

@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    """Fetch transactions of a user within a specified date range"""
    user_id = request.args.get("user_id")
    days = request.args.get("days", "30")  # Default to 30 days
    
    try:
        days = int(days)
        # Get current time in UTC with timezone awareness
        now = datetime.now(pytz.utc)
        start_date = now - timedelta(days=days)
        print(f"Fetching transactions from {start_date} to {now}")
        
        # Query transactions with date range filter
        txns = list(transactions.find({
            "user_id": user_id,
            "date": {
                "$gte": start_date,
                "$lte": now
            }
        }).sort("date", -1))
        
        # Format and return the transactions
        formatted_txns = []
        for txn in txns:
            txn["_id"] = str(txn["_id"])  # Convert ObjectId to string for JSON serialization
            txn["date"] = txn["date"].isoformat()  # Convert date to ISO format
            formatted_txns.append(txn)
        
        return jsonify(formatted_txns)
    
    except ValueError:
        return jsonify({"error": "Invalid 'days' parameter"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/summary", methods=["POST"])
def get_summary():
    """Generate a summary based on user's transactions"""
    try:
        user_id = request.json.get("user_id")
        txns = list(transactions.find({"user_id": user_id}))
        prompt = "Provide creative financial and environmental insights for these transactions:"
        summary = get_ai_response(prompt, txns)
        return jsonify({"summary": summary})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/suggestions", methods=["GET"])
def get_suggestions():
    """Generate suggestions to improve eco-friendly spending"""
    try:
        user_id = request.args.get("user_id")
        txns = list(transactions.find({"user_id": user_id}))
        prompt = "Give 5 actionable suggestions to improve eco-friendly spending:"
        suggestions = get_ai_response(prompt, txns)
        return jsonify({"suggestions": suggestions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/goals", methods=["POST"])
def set_goal():
    """Set a user's green score goal"""
    try:
        data = request.get_json()
        goal = {
            "user_id": data["user_id"],
            "target_score": data["target_score"],
            "target_date": datetime.strptime(data["target_date"], "%Y-%m-%d"),
            "created_at": datetime.utcnow(),
            "progress": 0
        }
        
        result = goals.insert_one(goal)
        return jsonify({
            "message": "Goal created",
            "goal_id": str(result.inserted_id)
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/ask-green", methods=["POST"])
def ask_green():
    """Answer a user query based on their transaction data"""
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        txns = list(transactions.find({"user_id": user_id}))
        prompt = f"User question: {data['question']}\n\nBased on these transactions:"
        answer = get_ai_response(prompt, txns)
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Auth Endpoints (Simplified)
@app.route("/api/register", methods=["POST"])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        if users.find_one({"user_id": data["email"]}):
            return jsonify({"error": "User already exists"}), 409
            
        user = {
            "user_id": data["email"],
            "green_score": 0,
            "account_number": data["account_number"],
            "account_type": "Eco-Saver",
            "balance": 0,
            "created_at": datetime.utcnow()
        }
        
        users.insert_one(user)
        return jsonify({"message": "User created successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/login", methods=["POST"])
def login():
    """Login a user"""
    try:
        data = request.get_json()
        user = users.find_one({"user_id": data["email"]})
        
        if user:
            return jsonify({"message": "Login successful"})
            
        return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Run the Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
