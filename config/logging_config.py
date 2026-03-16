# config/logging_config.py

import logging
import sys

# Why configure logging?
# Default Python logging is noisy and unformatted.
# This gives every log message a timestamp, level, and file name —
# so when CrewAI runs 4 agents in parallel, you can see exactly
# which agent produced which log line.

def setup_logging():
    logging.basicConfig(
        # Log to terminal (stdout)
        stream=sys.stdout,

        # Minimum level to show: DEBUG shows everything
        # In production you'd change this to INFO or WARNING
        level=logging.DEBUG,

        # Format: [TIME] LEVEL  filename:line_number  message
        # Example: [2024-01-15 10:23:45] INFO  web_agent.py:42  Starting scrape
        format="[%(asctime)s] %(levelname)-5s  %(filename)s:%(lineno)d  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Silence noisy third-party libraries that log too much
    # (these libraries log internal debug info we don't need to see)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("playwright").setLevel(logging.WARNING)


# Get a named logger — use this in every file instead of print()
# Usage: logger = get_logger(__name__)
# __name__ automatically becomes the module name e.g. "agents.web_agent"
def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)