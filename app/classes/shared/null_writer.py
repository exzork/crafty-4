import logging
import os

logger = logging.getLogger(__name__)


class NullWriter:
    def write(self, data):
        if os.environ["CRAFTY_LOG_NULLWRITER"] == "true":
            logger.debug(data)
