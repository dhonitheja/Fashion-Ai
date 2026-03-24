import httpx
import json

try:
    resp = httpx.post(
        "http://localhost:8000/api/generate",
        json={
            "description": "red dress under nighttime, dark ambient lighting with flash photography",
            "gender": "female",
            "person_type": "adult",
            "age": 25,
            "lighting": "night"
        },
        timeout=120
    )
    print("Status:", resp.status_code)
    try:
        print("Response JSON:", json.dumps(resp.json(), indent=2))
    except BaseException:
        print("Response Text:", resp.text)
except Exception as e:
    print("Error:", e)
