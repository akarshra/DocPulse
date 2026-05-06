from app.config import gemini_client
import sys

models = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3-flash-preview"]

for m in models:
    try:
        res = gemini_client.models.generate_content(model=m, contents="Say hi")
        print(f"{m} SUCCESS: {res.text}")
    except Exception as e:
        print(f"{m} FAILED: {e}")
