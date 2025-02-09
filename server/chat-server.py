from flask import Flask, request, jsonify
from flask_cors import CORS
import requests  # Import requests to make external API calls
from together import Together

app = Flask(__name__)

CORS(app)
CORS(app, origins=["http://localhost:5001"])  # Allow cross-origin requests from your frontend

# Replace with your actual API key.
client = Together(api_key="2c604a3524b37e3c06c59fe9738b59e952d4d761b57e9a9290e5d6c02e42f301")

@app.route('/chat', methods=['POST'])
def chat():
    """
    Expects a JSON payload with a "conversation" key. The value should be a list
    of messages, each message being a dict with "role" and "content" keys.
    
    The endpoint sends the conversation context to the Together API and returns
    the assistant's reply as JSON.
    """
    data = request.get_json()
    if not data or "conversation" not in data:
        return jsonify({"error": "No conversation provided in the payload."}), 400

    conversation = data["conversation"]

    # Step 1: Call the /api/transactions endpoint to get the transaction data
    try:
        response = requests.get('http://localhost:5001/api/transactions?user_id=nyu&days=30')  # Assuming the transactions API is local
        transactions = response.json()  # Assuming the response is in JSON format
        print(transactions)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Error fetching transactions: {str(e)}"}), 500

    # Step 2: Append transaction data to the conversation
    conversation.append({"role": "system", "content": f"Transactions: {transactions}"})

    # Step 3: Call the Together API with the updated conversation
    try:
        response_stream = client.chat.completions.create(
            model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo-128K",
            messages=conversation,
            max_tokens=None,  # Optionally, set a token limit here.
            temperature=0.7,
            top_p=0.7,
            top_k=50,
            repetition_penalty=1,
            stop=["<|eot_id|>", "<|eom_id|>"],
            stream=True
        )

        full_response = ""
        for token in response_stream:
            # Each token in the stream should have a 'choices' attribute.
            if hasattr(token, 'choices'):
                token_text = token.choices[0].delta.content
                full_response += token_text

        return jsonify({"assistant": full_response})

    except Exception as e:
        return jsonify({"error": f"Error calling Together API: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5002, debug=True)



# from flask import Flask, request, jsonify
# from together import Together

# from flask import Flask, request, jsonify
# from flask_cors import CORS 

# app = Flask(__name__)

# CORS(app)

# CORS(app, origins=["http://localhost:5001"])  

# # Replace with your actual API key.
# client = Together(api_key="2c604a3524b37e3c06c59fe9738b59e952d4d761b57e9a9290e5d6c02e42f301")

# @app.route('/chat', methods=['POST'])
# def chat():
#     """
#     Expects a JSON payload with a "conversation" key. The value should be a list
#     of messages, each message being a dict with "role" and "content" keys.
    
#     The endpoint sends the conversation context to the Together API and returns
#     the assistant's reply as JSON.
#     """
#     data = request.get_json()
#     if not data or "conversation" not in data:
#         return jsonify({"error": "No conversation provided in the payload."}), 400

#     conversation = data["conversation"]

#     # Call the Together API with streaming enabled. We collect the tokens
#     # and build the full assistant reply.
#     response_stream = client.chat.completions.create(
#         model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo-128K",
#         messages=conversation,
#         max_tokens=None,         # Optionally, set a token limit here.
#         temperature=0.7,
#         top_p=0.7,
#         top_k=50,
#         repetition_penalty=1,
#         stop=["<|eot_id|>", "<|eom_id|>"],
#         stream=True
#     )

#     full_response = ""
#     for token in response_stream:
#         # Each token in the stream should have a 'choices' attribute.
#         if hasattr(token, 'choices'):
#             token_text = token.choices[0].delta.content
#             full_response += token_text

#     # Optionally, you could append the assistant's reply to the conversation here.
#     # For now, we just return the assistant's reply.
#     return jsonify({"assistant": full_response})

# if __name__ == '__main__':
#     app.run(host="0.0.0.0", port=5002, debug=True)
