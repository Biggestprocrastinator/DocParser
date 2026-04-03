import requests
import base64
import os
import json

# Configuration
API_URL = "http://127.0.0.1:8000/api/document-analyze"
API_KEY = "your_api_key_here"
SAMPLES_DIR = "./test_samples"

def test_files():
    if not os.path.exists(SAMPLES_DIR):
        print(f"❌ Error: Folder '{SAMPLES_DIR}' not found.")
        return

    for filename in os.listdir(SAMPLES_DIR):
        file_path = os.path.join(SAMPLES_DIR, filename)
        
        # Determine file type
        ext = filename.split('.')[-1].lower()
        if ext not in ['pdf', 'png', 'jpg', 'jpeg', 'docx']:
            continue

        print(f"🔍 Testing: {filename}...")

        with open(file_path, "rb") as f:
            encoded_string = base64.b64encode(f.read()).decode('utf-8')

        payload = {
            "fileName": filename,
            "fileType": ext,
            "fileBase64": encoded_string
        }

        try:
            response = requests.post(
                API_URL, 
                headers={"x-api-key": API_KEY, "Content-Type": "application/json"}, 
                json=payload
            )
            
            # Print the result clearly
            if response.status_code in [200, 202]:
                data = response.json()
                
                # Check if it was sent to the background queue
                if data.get("status") == "processing":
                    task_id = data.get("task_id")
                    print(f"⏳ Document large, timed out! Celery is processing in background.")
                    print(f"🔄 Actively Polling Task ID: {task_id}...")
                    
                    import time
                    while True:
                        time.sleep(3) # Wait 3 seconds before pinging again
                        status_res = requests.get(
                            f"http://127.0.0.1:8000/api/document-status/{task_id}",
                            headers={"x-api-key": API_KEY}
                        )
                        
                        if status_res.status_code == 200:
                            status_data = status_res.json()
                            if status_data.get("status") == "success":
                                print(f"✅ Background Success | Summary: {status_data['summary'][:50]}...")
                                print(f"📊 Entities: {json.dumps(status_data['entities'], indent=2)}")
                                break
                            elif status_data.get("status") == "processing":
                                # Just print a dot to show we are still waiting
                                print("   ...", end="", flush=True)
                            else:
                                print(f"\n⚠️ Task Finished with Unknown Status: {status_data}")
                                break
                        else:
                            print(f"\n❌ Status Endpoint Error | Code: {status_res.status_code}")
                            break
                            
                # Check if it returned fast enough to skip the queue
                elif "summary" in data:
                    print(f"✅ Fast Success | Summary: {data['summary'][:50]}...")
                    print(f"📊 Entities: {json.dumps(data['entities'], indent=2)}")
                else:
                    print(f"⚠️ Unexpected Data Format: {data}")

            else:
                print(f"❌ Failed | Status: {response.status_code} | {response.text}")
        
        except Exception as e:
            print(f"💥 Error connecting to API: {e}")
        
        print("-" * 50)

if __name__ == "__main__":
    test_files()