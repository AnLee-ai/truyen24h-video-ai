import g4f
from g4f.client import Client

def test_g4f():
    print("Testing g4f...")
    client = Client()
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello, write a short joke in Vietnamese."}],
        )
        print("Auto Provider Response:", response.choices[0].message.content)
    except Exception as e:
        print("Auto Provider failed:", e)

if __name__ == "__main__":
    test_g4f()