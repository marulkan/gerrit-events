import logging
import logging.handlers
import argparse
import sys
import os
import yaml

from gerritevents import Log

log = Log(__name__)
version = '0.0.1'


class Launcher:
    LOG_ROTATE = 8  # Days

    def __init__(self, log_file=None, debug=False, config_file=None):
        self._log_file = log_file
        self._debug = debug
        self._config_file = config_file
        self.config = None

        # Use canonical paths
        if self._log_file:
            self._log_file = os.path.realpath(self._log_file)

    def _setup_logging(self):
        # Top-level logger
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        # Log format
        log_formatter = logging.Formatter(
            '%(asctime)s %(process)d %(levelname)s %(name)s %(message)s')

        # Rotating file logger
        if self._log_file:
            try:
                log_rotate = logging.handlers.TimedRotatingFileHandler(
                    self._log_file,
                    when='midnight',
                    backupCount=self.LOG_ROTATE)
            except IOError as e:
                log.error(event='logfile.error', error=e, path=self._log_file)
                sys.exit(1)
            log_rotate.setFormatter(log_formatter)
            if self._debug:
                log_rotate.setLevel(logging.DEBUG)
            else:
                log_rotate.setLevel(logging.INFO)
            logger.addHandler(log_rotate)

    def _setup_config(self):
        self.config = yaml.load(self._config_file)

    def start(self):
        """Launch application"""
        # Setup logging
        self._setup_logging()
        self._setup_config()

        # Application status
        success = None

        # Exit code
        exit_code = 255

        success = self.run()

        if success is True:
            exit_code = 0
        elif success is False:
            exit_code = 1
        return exit_code

    def run(self):
        """Override this method to start the application logic"""
        pass


class CliLauncher(Launcher):
    def __init__(self, raw_args=None):
        self.setup_parser()

        self.args = self.parser.parse_args(args=raw_args)

        super().__init__(
            debug=self.args.debug,
            log_file=self.args.log_file,
            config_file=self.args.config_file)

    def setup_parser(self, description=None):
        self.parser = argparse.ArgumentParser(description=description)

        # FIXME: version should be added.
        self.parser.add_argument(
            '-V', '--version', action='version', version=version)
        self.parser.add_argument(
            '--debug', action='store_true', help='turn on debug logging')
        self.parser.add_argument(
            '--config-file',
            type=argparse.FileType('r'),
            help="YAML formated configuration file")
        self.parser.add_argument(
            '--log-file', metavar='PATH', help='log file path')
