import sys

def fix_text(text):
    try:
        return text.encode('latin-1').decode('utf-8')
    except Exception as e:
        return f"Error: {e}"

print(fix_text("ThÃ¡ÂºÂ§n PhÃ¡"))
