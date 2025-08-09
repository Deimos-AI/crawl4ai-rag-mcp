import requests
from datetime import datetime
import json

# Test script with known hallucinations for testing

def main():
    # Valid code
    response = requests.get("https://api.example.com/data")
    
    # Hallucination 1: extract_json_data doesn't exist on Response object
    data = response.extract_json_data()
    
    # Valid code
    current_time = datetime.now()
    
    # Hallucination 2: add_days doesn't exist on datetime object
    tomorrow = current_time.add_days(1)
    
    # Hallucination 3: auto_retry parameter doesn't exist in requests.post
    result = requests.post(
        "https://api.example.com/submit",
        json={"data": "test"},
        auto_retry=True  # This parameter doesn't exist
    )
    
    # Valid code
    json_str = json.dumps({"test": "data"})
    
    # Hallucination 4: json.parse doesn't exist (should be json.loads)
    parsed = json.parse(json_str)
    
    return parsed

if __name__ == "__main__":
    main()