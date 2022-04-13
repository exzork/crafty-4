import datetime
import logging
import sys

logger = logging.getLogger(__name__)

try:
    from colorama import init
    from termcolor import colored

except ModuleNotFoundError as ex:
    logger.critical(f"Import Error: Unable to load {ex.name} module", exc_info=True)
    print(f"Import Error: Unable to load {ex.name} module")
    from app.classes.shared.installer import installer

    installer.do_install()


class Console:
    def __init__(self):
        if "colorama" in sys.modules:
            init()

    @staticmethod
    def do_print(message, color):
        if "termcolor" in sys.modules or "colorama" in sys.modules:
            print(colored(message, color))
        else:
            print(message)

    @staticmethod
    def magenta(message):
        Console.do_print(message, "magenta")

    @staticmethod
    def cyan(message):
        Console.do_print(message, "cyan")

    @staticmethod
    def yellow(message):
        Console.do_print(message, "yellow")

    @staticmethod
    def red(message):
        Console.do_print(message, "red")

    @staticmethod
    def green(message):
        Console.do_print(message, "green")

    @staticmethod
    def white(message):
        Console.do_print(message, "white")

    @staticmethod
    def debug(message):
        dt = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        Console.magenta(f"[+] Crafty: {dt} - DEBUG:\t{message}")

    @staticmethod
    def info(message):
        dt = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        Console.white(f"[+] Crafty: {dt} - INFO:\t{message}")

    @staticmethod
    def warning(message):
        dt = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        Console.cyan(f"[+] Crafty: {dt} - WARNING:\t{message}")

    @staticmethod
    def error(message):
        dt = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        Console.yellow(f"[+] Crafty: {dt} - ERROR:\t{message}")

    @staticmethod
    def critical(message):
        dt = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        Console.red(f"[+] Crafty: {dt} - CRITICAL:\t{message}")

    @staticmethod
    def help(message):
        dt = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        Console.green(f"[+] Crafty: {dt} - HELP:\t{message}")
