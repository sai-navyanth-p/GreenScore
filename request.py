import json
import requests

# Path to the JSON file with transactions.
# The file should contain a JSON object with a "transactions" key.
# Example:
# {
#   "transactions": [
#     {
#       "transactionId": "TXN1001",
#       "date": "2023-01-01",
#       "description": "Direct Deposit – Refund",
#       "type": "Credit",
#       "amount": "$186.27",
#       "balance": "$3,686.27",
#       "eco": "No",
#       "totalEco": "$0.00"
#     },
#     ...
#   ]
# }
file_path = "/Users/psainavyanth/Documents/NYU-Hackathon/GreenScore/client/data/transactions.json"

# Read the JSON file
with open(file_path, 'r') as file:
    payload = json.load(file)

# ----------------------------
# Test the /summary endpoint
# ----------------------------
url_summary = "http://127.0.0.1:5000/summary"
headers = {"Content-Type": "application/json"}

print("Testing /summary endpoint...")
response_summary = requests.post(url_summary, json=payload, headers=headers)
print("Status Code:", response_summary.status_code)
try:
    response_data = response_summary.json()
    print("Response JSON:")
    print(json.dumps(response_data, indent=2))
except ValueError:
    print("Response content is not valid JSON:")
    print(response_summary.text)


# -------------------------------
# Test the /suggestion endpoint
# -------------------------------
# For the /suggestion endpoint, the API expects a payload with a "transactions" key.
url_suggestion = "http://127.0.0.1:5000/suggestion"

print("\nTesting /suggestion endpoint...")
response_suggestion = requests.post(url_suggestion, json=payload, headers=headers)
print("Status Code:", response_suggestion.status_code)
# The suggestion endpoint returns plain text (streamed response)
print("Response Text:")
print(response_suggestion.text)


# import json
# import requests

# # Define the URL for the /chat endpoint.
# url = "http://127.0.0.1:5000/chat"

# # Build the conversation history as a list of messages.
# conversation = [
#     {
#         "role": "user",
#         "content": """Transaction ID,Date,Description,Type,Amount,Balance,Eco,Total eco products amounts
# TXN1001,2023-01-01,Direct Deposit – Refund,Credit,$186.27,"$3,686.27",No,$0.00
# TXN1002,2023-01-02,Online Purchase – Amazon,Debit,$158.38,"$3,527.89",Yes,$16.15
# TXN1003,2023-01-03,ATM Withdrawal,Debit,$140.25,"$3,387.64",No,$0.00
# TXN1004,2023-01-04,POS Purchase – Coffee Shop,Debit,$18.03,"$3,369.61",Yes,$1.81
# TXN1005,2023-01-05,Online Payment – Utilities,Debit,$128.84,"$3,240.77",No,$0.00

# I have a user.
# These are the user's recent transactions.
# Analyze these transactions and, using this data, suggest what he can buy in the future to improve his eco points and identify areas where he should reduce spending."""
#     }
# ]

# # Prepare the payload with the conversation history.
# payload = {"conversation": conversation}

# # Set the headers for JSON content.
# headers = {"Content-Type": "application/json"}

# # Send the POST request to the /chat endpoint.
# response = requests.post(url, json=payload, headers=headers)

# # Print the status code and the response content.
# print("Status Code:", response.status_code)

# try:
#     response_json = response.json()
#     print("Response JSON:")
#     print(json.dumps(response_json, indent=2))
# except ValueError:
#     print("Response content is not valid JSON:")
#     print(response.text)
