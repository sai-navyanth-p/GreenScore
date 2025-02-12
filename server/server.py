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
from flask_cors import CORS  # Import Flask-CORS
from together import Together

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:000"}})

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
            "userId": user_id,
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


client = Together(api_key="2c604a3524b37e3c06c59fe9738b59e952d4d761b57e9a9290e5d6c02e42f301")

@app.route("/api/summary", methods=["GET"])
def get_summary():
    """Generate a summary based on user's transactions"""
    try:
        user_id = request.args.get("user_id")  # GET requests use request.args, not request.json
        if not user_id:
            return jsonify({"error": "Missing user_id parameter"}), 400

        txns = list(transactions.find({"userId": user_id}))

        if not txns:
            return jsonify({"error": "No transactions found for the given user_id."}), 404

        # Constructing the transaction data in CSV format
        txn_data = "\n".join([f"{txn['transactionId']},{txn['date']},{txn['description']},{txn['type']},{txn['amount']},{txn['balance']},{txn['eco']},{txn['totalEco']}" for txn in txns])

        # Constructing the prompt to send to the model
        prompt = f"""
        Transaction ID,Date,Description,Type,Amount,Balance,Eco,Total eco products amounts
        {txn_data}

        I have a user whose transactions are listed above.
        Please summarize the user's spending behavior, focusing on eco-friendly transactions, identifying where they have spent the most, and whether they are taking actions that align with improving their eco points. Suggest how they can improve their eco points while maintaining a sustainable budget.
        """

        # Calling the chat completions API
        response = client.chat.completions.create(
            model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo-128K",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=None,
            temperature=0.7,
            top_p=0.7,
            top_k=50,
            repetition_penalty=1,
            stop=["<|eot_id|>", "<|eom_id|>"],
            stream=True
        )

        # Collecting the response stream
        summary = ""
        for token in response:
            if hasattr(token, 'choices'):
                summary += token.choices[0].delta.content
        
        return jsonify({"summary": summary.strip()})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/suggestions", methods=["GET"])
def get_suggestions():
    """Generate suggestions to improve eco-friendly spending"""
    try:
        user_id = request.args.get("user_id")  # GET requests use request.args, not request.json
        if not user_id:
            return jsonify({"error": "Missing user_id parameter"}), 400

        txns = list(transactions.find({"userId": user_id}))

        if not txns:
            return jsonify({"error": "No transactions found for the given user_id."}), 404

        # Constructing the transaction data in CSV format
        txn_data = "\n".join([f"{txn['transactionId']},{txn['date']},{txn['description']},{txn['type']},{txn['amount']},{txn['balance']},{txn['eco']},{txn['totalEco']}" for txn in txns])

        # Constructing the prompt to send to the model
        prompt = f"""
        Transaction ID,Date,Description,Type,Amount,Balance,Eco,Total eco products amounts
        {txn_data}

        I have a user whose transactions are listed above.
        Based on this data, please provide suggestions on how the user can improve their eco points by making better spending choices. 
        Consider products or services they should focus on buying to maximize eco points and areas where they should reduce spending for the environment. Additionally, if there are any habits they should change, suggest those as well.
        """

        # Calling the chat completions API
        response = client.chat.completions.create(
            model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo-128K",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=None,
            temperature=0.7,
            top_p=0.7,
            top_k=50,
            repetition_penalty=1,
            stop=["<|eot_id|>", "<|eom_id|>"],
            stream=True
        )

        # Collecting the response stream
        suggestions = ""
        for token in response:
            if hasattr(token, 'choices'):
                suggestions += token.choices[0].delta.content

        return jsonify({"suggestions": suggestions.strip()})

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
