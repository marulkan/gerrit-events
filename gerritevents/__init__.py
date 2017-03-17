import logging

class Log:
    def __init__(self, name):
        self.logger = logging.getLogger(name)

    def log(self, lvl, event=None, **kwargs):
        assert (event)
        msg_items = ['event=%s' % event] + \
                    ['%s="%s"' % (k, v) for k, v in kwargs.items()]
        self.logger.log(lvl, ' '.join(msg_items))

    def debug(self, **kwargs):
        self.log(logging.DEBUG, **kwargs)

    def info(self, **kwargs):
        self.log(logging.INFO, **kwargs)

    def warning(self, **kwargs):
        self.log(logging.WARNING, **kwargs)

    def error(self, **kwargs):
        self.log(logging.ERROR, **kwargs)

    def critical(self, **kwargs):
        self.log(logging.CRITICAL, **kwargs)