import os.path
from typing import Any, Dict

from chaoslib.exceptions import ActivityFailed
from logzero import logger

__all__ = ["should_not_have_any_errors", "error_count_should_not_grow"]


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


def error_count_should_not_grow(value: Dict[str, Any] = None) -> bool:
    """
    Go through all the error counts and raise an error when we notice an
    increase.
    """
    values = value["data"]["result"][0]["values"]
    if not values:
        return True

    values = set(values[1:len(values):2])
    if len(values) > 1:
        raise ActivityFailed("Error counts: {}".format(values))

    return True