import builtins
import logging

"""
disable_logs.disable_logs()

Replaces built-in print with a noop and disables root logging handlers.
Designed to be safe to import: if something fails the function is a no-op.
"""

def disable_logs():
    try:
        builtins.print = lambda *args, **kwargs: None
    except Exception:
        pass

    try:
        # Remove handlers from root logger and disable lower-severity logs
        root = logging.getLogger()
        root.handlers = []
        logging.disable(logging.CRITICAL)
    except Exception:
        pass
