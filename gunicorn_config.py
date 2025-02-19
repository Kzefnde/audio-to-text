import multiprocessing

# Базовые настройки
bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"
worker_connections = 1000
timeout = 120

# Настройки логирования
accesslog = "-"  # логирование в stdout
errorlog = "-"   # логирование в stderr
loglevel = "info"

# Настройки процесса
daemon = False
pidfile = "gunicorn.pid"
umask = 0
user = None
group = None
tmp_upload_dir = None

# Настройки SSL (если нужно)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile" 