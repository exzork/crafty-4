import datetime
import logging
from sys import modules

logger = logging.getLogger(__name__)

try:
    from colorama import init
    from termcolor import colored

except ModuleNotFoundError as e:
    logging.critical("Import Error: Unable to load {} module".format(e, e.name))
    print("Import Error: Unable to load {} module".format(e, e.name))
    pass


class Console:

    def __init__(self):
        if 'colorama' in modules:
            init()

    @staticmethod
    def do_print(message, color):
        if 'termcolor' in modules or 'colorama' in modules:
            print(colored(message, color))
        else:
            print(message)

    def magenta(self, message):
        self.do_print(message, "magenta")

    def cyan(self, message):
        self.do_print(message, "cyan")

    def yellow(self, message):
        self.do_print(message, "yellow")

    def red(self, message):
        self.do_print(message, "red")

    def green(self, message):
        self.do_print(message, "green")

    def white(self, message):
        self.do_print(message, "white")

    def debug(self, message):
        dt = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        self.magenta("[+] Crafty: {} - DEBUG:\t{}".format(dt, message))

    def info(self, message):
        dt = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        self.white("[+] Crafty: {} - INFO:\t{}".format(dt, message))

    def warning(self, message):
        dt = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        self.cyan("[+] Crafty: {} - WARNING:\t{}".format(dt, message))

    def error(self, message):
        dt = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        self.yellow("[+] Crafty: {} - ERROR:\t{}".format(dt, message))

    def critical(self, message):
        dt = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        self.red("[+] Crafty: {} - CRITICAL:\t{}".format(dt, message))

    def help(self, message):
        dt = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        self.green("[+] Crafty: {} - HELP:\t{}".format(dt, message))


console = Console()

