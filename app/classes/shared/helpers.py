import os
import sys
import json
import uuid
import string
import base64
import socket
import random
import logging
import configparser
from datetime import datetime
from socket import gethostname

from app.classes.shared.console import console

logger = logging.getLogger(__name__)

try:
    from OpenSSL import crypto
    from argon2 import PasswordHasher

except ModuleNotFoundError as e:
    logger.critical("Import Error: Unable to load {} module".format(e, e.name))
    console.critical("Import Error: Unable to load {} module".format(e, e.name))
    sys.exit(1)

class Helpers:

    def __init__(self):
        self.root_dir = os.path.abspath(os.path.curdir)
        self.config_dir = os.path.join(self.root_dir, 'app', 'config')
        self.session_file = os.path.join(self.root_dir, 'session.lock')
        self.settings_file = os.path.join(self.root_dir, 'config.ini')
        self.webroot = os.path.join(self.root_dir, 'app', 'frontend')
        self.db_path = os.path.join(self.root_dir, 'commander.sqlite')
        self.passhasher = PasswordHasher()
        self.exiting = False

    def get_setting(self, section, key):

        try:
            our_config = configparser.ConfigParser()
            our_config.read(self.settings_file)

            if our_config.has_option(section, key):
                return our_config[section][key]

        except Exception as e:
            logger.critical("Config File Error: Unable to read {} due to {}".format(self.settings_file, e))
            console.critical("Config File Error: Unable to read {} due to {}".format(self.settings_file, e))

        return False

    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    def get_version(self):
        version_data = {}
        try:
            with open(os.path.join(self.config_dir, 'version.json'), 'r') as f:
                version_data = json.load(f)

        except Exception as e:
            console.critical("Unable to get version data!")

        return version_data

    def do_exit(self):
        exit_file = os.path.join(self.root_dir, 'exit.txt')
        try:
            open(exit_file, 'a').close()

        except Exception as e:
            logger.critical("Unable to create exit file!")
            console.critical("Unable to create exit file!")
            sys.exit(1)

    def encode_pass(self, password):
        return self.passhasher.hash(password)

    def verify_pass(self, password, currenthash):
        try:
            self.passhasher.verify(currenthash, password)
            return True
        except:
            pass
            return False

    @staticmethod
    def check_writeable(path: str):
        filename = os.path.join(path, "tempfile.txt")
        try:
            fp = open(filename, "w").close()
            os.remove(filename)

            logger.info("{} is writable".format(filename))
            return True

        except Exception as e:
            logger.critical("Unable to write to {} - Error: {}".format(path, e))
            return False

    def ensure_logging_setup(self):
        log_file = os.path.join(os.path.curdir, 'logs', 'commander.log')

        logger.info("Checking app directory writable")

        writeable = self.check_writeable(self.root_dir)

        # if not writeable, let's bomb out
        if not writeable:
            logger.critical("Unable to write to {} directory!".format(self.root_dir))
            sys.exit(1)

        # ensure the log directory is there
        try:
            os.makedirs(os.path.join(self.root_dir, 'logs'))
        except Exception as e:
            pass

        # ensure the log file is there
        try:
            open(log_file, 'a').close()
        except Exception as e:
            console.critical("Unable to open log file!")
            sys.exit(1)

        # del any old session.lock file as this is a new session
        try:
            os.remove(self.session_file)
        except:
            pass

    @staticmethod
    def get_time_as_string():
        now = datetime.now()
        return now.strftime("%m/%d/%Y, %H:%M:%S")

    @staticmethod
    def check_file_exists(path: str):
        logger.debug('Looking for path: {}'.format(path))

        if os.path.exists(path) and os.path.isfile(path):
            logger.debug('Found path: {}'.format(path))
            return True
        else:
            return False

    @staticmethod
    def human_readable_file_size(num: int, suffix='B'):
        for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f%s%s" % (num, 'Y', suffix)

    @staticmethod
    def check_path_exits(path: str):
        logger.debug('Looking for path: {}'.format(path))

        if os.path.exists(path):
            logger.debug('Found path: {}'.format(path))
            return True
        else:
            return False

    @staticmethod
    def get_file_contents(path: str, lines=100):

        contents = ''

        if os.path.exists(path) and os.path.isfile(path):
            try:
                with open(path, 'r') as f:
                    for line in (f.readlines() [-lines:]):
                        contents = contents + line

                return contents

            except Exception as e:
                logger.error("Unable to read file: {}. \n Error: ".format(path, e))
                return False
        else:
            logger.error("Unable to read file: {}. File not found, or isn't a file.".format(path))
            return False

    def create_session_file(self, ignore=False):

        if ignore and os.path.exists(self.session_file):
            os.remove(self.session_file)

        if os.path.exists(self.session_file):

            file_data = self.get_file_contents(self.session_file)
            try:
                data = json.loads(file_data)
                pid = data.get('pid')
                started = data.get('started')
                console.critical("Another commander agent seems to be running...\npid: {} \nstarted on: {}".format(pid, started))
            except Exception as e:
                pass

            sys.exit(1)

        pid = os.getpid()
        now = datetime.now()

        session_data = {
            'pid': pid,
            'started': now.strftime("%d-%m-%Y, %H:%M:%S")
            }
        with open(self.session_file, 'w') as f:
            json.dump(session_data, f, indent=True)

    # because this is a recursive function, we will return bytes, and set human readable later
    def get_dir_size(self, path: str):
        total = 0
        for entry in os.scandir(path):
            if entry.is_dir(follow_symlinks=False):
                total += self.get_dir_size(entry.path)
            else:
                total += entry.stat(follow_symlinks=False).st_size
        return total

    @staticmethod
    def base64_encode_string(string: str):
        s_bytes = str(string).encode('utf-8')
        b64_bytes = base64.encodebytes(s_bytes)
        return b64_bytes.decode('utf-8')

    @staticmethod
    def base64_decode_string(string: str):
        s_bytes = str(string).encode('utf-8')
        b64_bytes = base64.decodebytes(s_bytes)
        return b64_bytes.decode("utf-8")

    def create_uuid(self):
        id = str(uuid.uuid4())
        return self.base64_encode_string(id).replace("\n", '')

    def ensure_dir_exists(self, path):
        """
        ensures a directory exists

        Checks for the existence of a directory, if the directory isn't there, this function creates the directory

        Args:
            path (string): the path you are checking for

        """

        try:
            os.makedirs(path)
            logger.debug("Created Directory : {}".format(path))

        # directory already exists - non-blocking error
        except FileExistsError:
            pass

    def create_self_signed_cert(self, cert_dir=None):

        if cert_dir is None:
            cert_dir = os.path.join(self.config_dir, 'web', 'certs')

        # create a directory if needed
        self.ensure_dir_exists(cert_dir)

        cert_file = os.path.join(cert_dir, 'commander.cert.pem')
        key_file = os.path.join(cert_dir, 'commander.key.pem')

        logger.info("SSL Cert File is set to: {}".format(cert_file))
        logger.info("SSL Key File is set to: {}".format(key_file))

        # don't create new files if we already have them.
        if self.check_file_exists(cert_file) and self.check_file_exists(key_file):
            logger.info('Cert and Key files already exists, not creating them.')
            return True

        console.info("Generating a self signed SSL")
        logger.info("Generating a self signed SSL")

        # create a key pair
        logger.info("Generating a key pair. This might take a moment.")
        console.info("Generating a key pair. This might take a moment.")
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, 4096)

        # create a self-signed cert
        cert = crypto.X509()
        cert.get_subject().C = "US"
        cert.get_subject().ST = "Georgia"
        cert.get_subject().L = "Atlanta"
        cert.get_subject().O = "Crafty Controller"
        cert.get_subject().OU = "Server Ops"
        cert.get_subject().CN = gethostname()
        cert.set_serial_number(1000)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(k)
        cert.sign(k, 'sha256')

        f = open(cert_file, "w")
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode())
        f.close()

        f = open(key_file, "w")
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k).decode())
        f.close()

    @staticmethod
    def random_string_generator(size=6, chars=string.ascii_uppercase + string.digits):
        """
        Example Usage
        random_generator() = G8sjO2
        random_generator(3, abcdef) = adf
        """
        return ''.join(random.choice(chars) for x in range(size))


helper = Helpers()
