
from langflix.core.redis_client import get_redis_job_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def force_release_lock():
    manager = get_redis_job_manager()
    logger.info("Forcing release of processor lock...")
    if manager.release_processor_lock():
        logger.info("✅ Lock released successfully.")
    else:
        # If normal release fails (e.g. key doesn't exist), force delete just in case
        logger.info("Standard release returned False (key might not exist). Ensuring deletion...")
        try:
            manager.redis_client.delete("jobs:processor_lock")
            logger.info("Force delete executed.")
        except Exception as e:
            logger.error(f"Error force deleting lock: {e}")

if __name__ == "__main__":
    force_release_lock()
