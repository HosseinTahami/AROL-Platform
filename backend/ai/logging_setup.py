import logging
import os

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

orchestrator_logger = logging.getLogger("orchestrator")
orchestrator_logger.setLevel(logging.INFO)

if not orchestrator_logger.handlers:
    handler = logging.FileHandler(os.path.join(LOG_DIR, "orchestrator.log"))
    formatter = logging.Formatter("%(asctime)s | %(message)s")
    handler.setFormatter(formatter)
    orchestrator_logger.addHandler(handler)