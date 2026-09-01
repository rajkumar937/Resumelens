"""Production WSGI entry point.

Run with a real WSGI server, e.g.:
    gunicorn -w 2 -b 0.0.0.0:$PORT wsgi:app

Do not use this for the Windows desktop build — that still uses run.py.
"""

import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Fallback for platforms that just run `python wsgi.py`
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
