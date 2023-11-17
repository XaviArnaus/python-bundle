from pyxavi.config import Config
from pyxavi.dictionary import Dictionary
from logging.handlers import TimedRotatingFileHandler
from datetime import time
from logging import Logger as OriginalLogger
import logging
import sys
import os


class Logger:
    """Class to help on instantiating Logging

    It uses the built-in logging infra, but takes the
    configuration from the given config object.

    It is meant to be used the first time in the initial
    executor, then passed through the code.

    The built-in logging system can also be used to pick up
    an already instantiated logger with this class,
    making it very versatile.

    :Authors:
        Xavier Arnaus <xavi@arnaus.net>

    """

    DEFAULT_LOG_FORMAT = "[%(asctime)s] %(levelname)-8s %(name)-12s %(message)s"
    DEFAULT_FILE_LOGGING = {
        "active": False,
        "filename": "debug.log",
        "rotate_files": False,
        # "S" | "M" | "H" | "D" | "W0"-"W6" | "midnight"
        "when_rotate": "midnight",
        # How many old rotated log files to keep
        "backup_count": 10,
        "encoding": "UTF-8",
        "utc": False,
        # Hour, Minute, Second
        "at_time": (1,0,0)
    }
    DEFAULT_STDOUT_LOGGING = {"active": False}
    DEFAULT_LOG_LEVEL = 20
    DEFAULT_LOGGER_NAME = "custom_logger"

    DEFAULTS = {
        # Common parameters
        "name": "custom_logger",
        "loglevel": 20,
        "format": "[%(asctime)s] %(levelname)-8s %(name)-12s %(message)s",
        # File logging
        "file": {
            "active": False,
            "filename": "debug.log",
            "encoding": "UTF-8",
            "rotate": {
                "active": False,
                "when": "midnight",
                "backup_count": 10,
                "utc": False,
                "at_time": (1,0,0)
            },
        },
        # Standard output logging
        "stdout": {
            "active": False
        }
    }

    _logger: OriginalLogger = None
    _base_path: str = None
    _logger_config: Dictionary = None
    _handlers = []

    def __init__(self, config: Config, base_path: str = None) -> None:

        self._base_path = base_path
        self._load_config(config=config)

        # Setting up the handlers straight away
        self._clean_handlers()
        self._set_handlers()

        # Define basic configuration
        logging.basicConfig(
            # Define logging level
            level=self._logger_config.get("loglevel"),
            # Define the format of log messages
            format=self._logger_config.get("format"),
            # Declare handlers
            handlers=self._handlers
        )
        # Define your own logger name
        self._logger = logging.getLogger(self._logger_config.get("name"))
    
    def _load_config(self, config: Config) -> None:
        # We may receive the old config, so here the strategy:
        #   1. Try to read the old config. No defaults, empty spaces as None.
        #   2. Try to read the new config. No defaults, empty spaces as None.
        #   3. Merge the objects, intersecting with preference to whoever is not None.
        #   4. Load the defaults
        #   5. Merge the intersected config over the defaults.
        #   6. Do the normal amends (base path on filename, calculation of at_time)
        #   7. Set the config data as usual.
        #
        old_config_values = self._load_old_config_without_defaults(config=config)
        new_config_values = self._load_new_config_without_defaults(config=config)
        intersected = {
            "name": new_config_values.get("logger.name", old_config_values.get("logger.name")),
            "loglevel": new_config_values.get("logger.loglevel", old_config_values.get("logger.loglevel")),
            "format": new_config_values.get("logger.format", old_config_values.get("logger.format")),
            # File logging
            "file": {
                "active": new_config_values.get("logger.file.active", old_config_values.get("logger.to_file")),
                "filename": new_config_values.get("logger.file.filename", old_config_values.get("logger.filename")),
                "encoding": new_config_values.get("logger.file.encoding"),
                "rotate": {
                    "active": new_config_values.get("logger.file.rotate.active"),
                    "when": new_config_values.get("logger.file.rotate.when"),
                    "backup_count": new_config_values.get("logger.file.rotate.backup_count"),
                    "utc": new_config_values.get("logger.file.rotate.utc"),
                    "at_time": new_config_values.get("logger.file.rotate.at_time")
                },
            },
            # Standard output logging
            "stdout": {
                "active": new_config_values.get("logger.stdout.active", old_config_values.get("logger.to_stdout"))
            }
        }
        defaults = Dictionary({"logger": self.DEFAULTS})
        defaults.merge(Dictionary(intersected))

        # And now the proper work:
        filename = defaults.get("logger.file.filename")
        if self._base_path is not None:
            defaults.set("logger.file.filename", os.path.join(self._base_path, filename))
        defaults.set("logger.file.rotate.at_time", time(*defaults.get("logger.file.rotate.at_time")))
        self._logger_config = defaults
        
        #
        # Uncoment the following code once the deprecation is expired and the old support code above is gone
        #
        # Previous work
        # filename = config.get("logger.file.filename", self.DEFAULT_FILE_LOGGING["file"]["filename"])
        # if self._base_path is not None:
        #     filename = os.path.join(self._base_path, filename)

        # # What we do here is to build a main dict where we ensure we always have a value.
        # self._logger_config = Dictionary({
        #     # Common parameters
        #     "name": config.get("logger.name", self.DEFAULTS["name"]),
        #     "loglevel": config.get("logger.loglevel", self.DEFAULTS["loglevel"]),
        #     "format": config.get("logger.format", self.DEFAULTS["format"]),
        #     # File logging
        #     "file": {
        #         "active": config.get("logger.file.active", self.DEFAULTS["file"]["active"]),
        #         "filename": filename,
        #         "encoding": config.get("logger.file.encoding", self.DEFAULTS["file"]["encoding"]),
        #         "rotate": {
        #             "active": config.get("logger.file.rotate.active", self.DEFAULTS["file"]["rotate"]["active"]),
        #             "when": config.get("logger.file.rotate.when", self.DEFAULTS["file"]["rotate"]["when"]),
        #             "backup_count": config.get("logger.file.rotate.backup_count", self.DEFAULTS["file"]["rotate"]["backup_count"]),
        #             "utc": config.get("logger.file.rotate.utc", self.DEFAULTS["file"]["rotate"]["utc"]),
        #             "at_time": time(*config.get("logger.file.rotate.at_time", self.DEFAULTS["file"]["rotate"]["at_time"]))
        #         },
        #     },
        #     # Standard output logging
        #     "stdout": {
        #         "active": config.get("logger.stdout.active", self.DEFAULTS["stdout"]["active"])
        #     }
        # })


    def _load_old_config_without_defaults(self, config: Config) -> Dictionary:
        # Previous work
        filename = config.get("logger.filename")
        if self._base_path is not None:
            filename = os.path.join(self._base_path, filename)

        # What we do here is to build a main dict where we ensure we always have a value.
        return Dictionary({
            # Common parameters
            "name": config.get("logger.name"),
            "loglevel": config.get("logger.loglevel"),
            "format": config.get("logger.format"),
            # File logging
            "file": {
                "active": config.get("logger.to_file"),
                "filename": filename
            },
            # Standard output logging
            "stdout": {
                "active": config.get("logger.to_stdout")
            }
        })
    

    def _load_new_config_without_defaults(self, config: Config) -> Dictionary:
        # Previous work
        filename = config.get("logger.file.filename")
        if self._base_path is not None:
            filename = os.path.join(self._base_path, filename)

        # What we do here is to build a main dict where we ensure we always have a value.
        return Dictionary({
            # Common parameters
            "name": config.get("logger.name"),
            "loglevel": config.get("logger.loglevel"),
            "format": config.get("logger.format"),
            # File logging
            "file": {
                "active": config.get("logger.file.active"),
                "filename": filename,
                "encoding": config.get("logger.file.encoding"),
                "rotate": {
                    "active": config.get("logger.file.rotate.active"),
                    "when": config.get("logger.file.rotate.when"),
                    "backup_count": config.get("logger.file.rotate.backup_count"),
                    "utc": config.get("logger.file.rotate.utc"),
                    "at_time": time(*config.get("logger.file.rotate.at_time"))
                },
            },
            # Standard output logging
            "stdout": {
                "active": config.get("logger.stdout.active")
            }
        })
    
    def _set_handlers(self) -> None:
        if self._logger_config.get("file.active"):
            if self._logger_config.get("file.rotate.active"):
                self._handlers.append(
                    TimedRotatingFileHandler(
                        filename=self._logger_config.get("file.filename"),
                        when=self._logger_config.get("file.rotate.when"),
                        backupCount=self._logger_config.get("file.rotate.backup_count"),
                        encoding=self._logger_config.get("file.encoding"),
                        utc=self._logger_config.get("file.rotate.utc"),
                        atTime=self._logger_config.get("file.rotate.at_time"),
                    )
                )
            else:
                self._handlers.append(
                    logging.FileHandler(
                        filename=self._logger_config.get("file.filename"),
                        mode='a',
                        encoding=self._logger_config.get("file.encoding")
                    )
                )

        if self._logger_config.get("stdout.active"):
            self._handlers.append(logging.StreamHandler(sys.stdout))
    

    def _clean_handlers(self) -> None:
        if self._logger is not None and self._logger.hasHandlers():
            self._logger.handlers.clear()
        if len(self._handlers) > 0:
            self._handlers = []
        

    def get_logger(self) -> OriginalLogger:
        return self._logger
