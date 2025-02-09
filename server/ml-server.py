from flask import Flask, request, Response, jsonify
from together import Together
import pandas as pd

app = Flask(__name__)

# Replace with your actual API key
client = Together(api_key="2c604a3524b37e3c06c59fe9738b59e952d4d761b57e9a9290e5d6c02e42f301")

def process_transactions(data):
    # Extract transactions list from JSON payload
    transactions = data.get('transactions', [])
    if not transactions:
        return None, "No transactions found in the payload."

    # Create a DataFrame from the transactions list
    df = pd.DataFrame(transactions)

    # Preprocess the 'amount' and 'totalEco' columns: remove $ and commas then convert to float.
    df['amount'] = df['amount'].str.replace(r'[$,]', '', regex=True).astype(float)
    df['totalEco'] = df['totalEco'].str.replace(r'[$,]', '', regex=True).astype(float)

    # Compute summary statistics
    total_transactions = len(df)
    total_credit = df[df['type'] == 'Credit']['amount'].sum()
    total_debit = df[df['type'] == 'Debit']['amount'].sum()
    eco_transactions = df[df['eco'] == 'Yes']
    eco_transaction_count = len(eco_transactions)
    total_eco_amount = eco_transactions['totalEco'].sum()

    summary = {
        "totalTransactions": total_transactions,
        "totalCredit": total_credit,
        "totalDebit": total_debit,
        "ecoTransactionCount": eco_transaction_count,
        "totalEcoAmount": total_eco_amount
    }

    # Create a detailed summary string.
    detailed_summary = (
        f"There are {total_transactions} transactions in total.\n"
        f"Total Credit Amount: ${total_credit:.2f}.\n"
        f"Total Debit Amount: ${total_debit:.2f}.\n"
        f"There are {eco_transaction_count} eco-friendly transactions with a total eco product amount of ${total_eco_amount:.2f}."
    )

    return {
        "detailedSummary": detailed_summary,
        "summary": summary
    }, None

@app.route('/summary', methods=['POST'])
def summary():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON payload provided"}), 400

    transactions = data.get('transactions', [])
    if not transactions:
        return jsonify({"error": "No transactions found in the payload."}), 400

    # Convert the transactions list to CSV format.
    df = pd.DataFrame(transactions)
    csv_data = df.to_csv(index=False)

    # Build the prompt using the CSV data and the summary instructions.
    prompt = f"""
{csv_data}

I have a user.
These are the user's recent transactions.
Analyze these transactions and provide a summary including:
1. The total number of transactions.
2. The total credit amount.
3. The total debit amount.
4. The total number of eco-friendly transactions.
5. The total amount of eco-friendly products.

Provide the summary in a human-readable format, similar to the following example:
"There are X transactions in total.
Total Credit Amount: $Y.
Total Debit Amount: $Z.
There are W eco-friendly transactions with a total eco product amount of $A."
    """

    # Call the Together chat completions endpoint with streaming enabled.
    together_response = client.chat.completions.create(
        model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo-128K",
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=None,         # Optionally set a limit
        temperature=0.7,
        top_p=0.7,
        top_k=50,
        repetition_penalty=1,
        stop=["<|eot_id|>", "<|eom_id|>"],
        stream=True
    )

    # Generator to yield each token as it arrives from the Together API.
    def generate():
        for token in together_response:
            if hasattr(token, 'choices'):
                content = token.choices[0].delta.content
                if content:
                    yield content

    # Return the streaming response as plain text.
    return Response(generate(), mimetype="text/plain")


@app.route('/suggestion', methods=['POST'])
def suggestion():
    # Expecting a JSON payload with a "transactions" key
    req_data = request.get_json()
    if not req_data:
        return jsonify({"error": "No JSON payload provided"}), 400

    transactions = req_data.get("transactions")
    if not transactions:
        return jsonify({"error": "No transactions provided in the payload"}), 400

    # Convert the transactions list to CSV format.
    df = pd.DataFrame(transactions)
    csv_data = df.to_csv(index=False)

    # Build the prompt using the CSV data and the analysis instructions.
    prompt = f"""
{csv_data}

I have a user.
These are the user's recent transactions.
Analyze these transactions and, using this data, suggest what he can buy in the future to improve his eco points and identify areas where he should reduce spending.
"""

    # Call the Together chat completions endpoint with streaming enabled.
    together_response = client.chat.completions.create(
        model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo-128K",
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=None,         # Optionally set a limit
        temperature=0.7,
        top_p=0.7,
        top_k=50,
        repetition_penalty=1,
        stop=["<|eot_id|>", "<|eom_id|>"],
        stream=True
    )

    # Generator to yield each token as it arrives from the Together API.
    def generate():
        for token in together_response:
            if hasattr(token, 'choices'):
                content = token.choices[0].delta.content
                if content:
                    yield content

    # Return the streaming response as plain text.
    return Response(generate(), mimetype="text/plain")

if __name__ == '__main__':
    app.run(debug=True)
