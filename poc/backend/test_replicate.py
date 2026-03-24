import httpx
import os
from dotenv import load_dotenv

load_dotenv("d:/Ideas/Sahion/poc/backend/.env")

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
print("Token exists:", bool(REPLICATE_API_TOKEN))

try:
    resp = httpx.post(
        "https://api.replicate.com/v1/predictions",
        headers={"Authorization": f"Token {REPLICATE_API_TOKEN}"},
        json={
            "version": "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
            "input": {"prompt": "test shirt", "width": 512, "height": 512}
        }
    )
    print("Replicate Status:", resp.status_code)
    print("Replicate Response:", resp.text)
except Exception as e:
    print("Exception:", e)
