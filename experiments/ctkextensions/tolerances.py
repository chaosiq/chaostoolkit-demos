import os.path

from logzero import logger

__all__ = ["should_not_have_any_errors"]


def should_not_have_any_errors(filepath: str) -> bool:
    """
    Simple function that acts as a tolerance validator for the term "error"
    in a given file.
    """
    if not os.path.isfile(filepath):
        return True

    with open(filepath) as f:
        for l in f:
            if "error" in l:
                logger.error("Found an error in traces")
                return False
    return True
