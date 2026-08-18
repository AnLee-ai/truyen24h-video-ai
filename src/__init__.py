import sys

# Fix Windows console UnicodeEncodeError for Vietnamese characters globally when 'src' is imported
try:
    if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
