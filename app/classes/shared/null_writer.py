import logging
import os

logger = logging.getLogger(__name__)


class NullWriter:
    def write(self, data):
        if os.environ.get("CRAFTY_LOG_NULLWRITER", "false") == "true":
            logger.debug(data)
        if os.environ.get("CRAFTY_PRINT_NULLWRITER", "false") == "true":
            print(data)
