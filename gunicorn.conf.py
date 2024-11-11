timeout = 600  # 10 minutes
workers = 3
worker_class = 'uvicorn.workers.UvicornWorker'  # For async support

accesslog = '-'  # Log to stdout
errorlog = '-'  # Log to stderr
loglevel = 'info'