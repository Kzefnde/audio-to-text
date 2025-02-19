import os
import platform
from main import app

def run_server():
    system = platform.system().lower()
    
    if system == 'windows':
        # Запуск на Windows через waitress
        from waitress import serve
        print("Starting server on http://localhost:8000 (Windows - Waitress)")
        serve(app, host="0.0.0.0", port=8000)
    else:
        # Запуск на Linux через gunicorn
        import subprocess
        print("Starting server on http://localhost:8000 (Linux - Gunicorn)")
        subprocess.run([
            "gunicorn",
            "-c", "gunicorn_config.py",
            "main:app"
        ])

if __name__ == "__main__":
    run_server() 