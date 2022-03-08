import datetime
import logging
import sys

from app.classes.shared.helpers import helper

try:
    from colorama import init
    from termcolor import colored

except ModuleNotFoundError as e:
    helper.auto_installer_fix(e)

logger = logging.getLogger(__name__)

class Console:

    def __init__(self):
        if 'colorama' in sys.modules:
            init()

    @staticmethod
    def do_print(message, color):
        if 'termcolor' in sys.modules or 'colorama' in sys.modules:
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
        self.magenta(f"[+] Crafty: {dt} - DEBUG:\t{message}")

    def info(self, message):
        dt = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        self.white(f"[+] Crafty: {dt} - INFO:\t{message}")

    def warning(self, message):
        dt = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        self.cyan(f"[+] Crafty: {dt} - WARNING:\t{message}")

    def error(self, message):
        dt = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        self.yellow(f"[+] Crafty: {dt} - ERROR:\t{message}")

    def critical(self, message):
        dt = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        self.red(f"[+] Crafty: {dt} - CRITICAL:\t{message}")

    def help(self, message):
        dt = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        self.green(f"[+] Crafty: {dt} - HELP:\t{message}")


console = Console()
