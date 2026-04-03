import requests
import base64
import json

# 1. Update the path to your DOCX file
DOCX_PATH = "E:/College/Clg receipts/r7.pdf"
URL = "http://127.0.0.1:8000/api/document-analyze"
HEADERS = {"x-api-key": "sk_track2_987654321", "Content-Type": "application/json"}

# 2. Read and encode the document
with open(DOCX_PATH, "rb") as doc_file:
    encoded_string = base64.b64encode(doc_file.read()).decode('utf-8')

# 3. Update the payload to reflect the 'docx' type
payload = {
    "fileName": "r7.pdf",
    "fileType": "pdf",  # Critical: Changed from 'image' to 'docx'
    "fileBase64": encoded_string
}

# 4. Send and print the response
response = requests.post(URL, headers=HEADERS, json=payload)
print(json.dumps(response.json(), indent=2))