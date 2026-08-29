import google.generativeai as genai
import os
from dotenv import load_dotenv
load_dotenv('.env', override=True)
raw_key = os.getenv('GEMINI_API_KEY')
api_key = raw_key.strip().strip('').strip('"') if raw_key else ""
print(f'Testing new API key ending in: {api_key[-4:]}' if api_key else 'No API key found in environment.')

try:
    genai.configure(api_key=api_key)
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f'Success! Found model: {m.name}')
            break
except Exception as e:
    print('Error:', e)
