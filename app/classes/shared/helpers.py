import os
import re
import sys
import json
import time
import uuid
import string
import base64
import socket
import random
import logging

from datetime import datetime
from socket import gethostname


from app.classes.shared.console import console

logger = logging.getLogger(__name__)

try:
    import requests
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
        self.webroot = os.path.join(self.root_dir, 'app', 'frontend')
        self.servers_dir = os.path.join(self.root_dir, 'servers')

        self.session_file = os.path.join(self.root_dir, 'app', 'config', 'session.lock')
        self.settings_file = os.path.join(self.root_dir, 'app', 'config', 'config.json')

        self.ensure_dir_exists(os.path.join(self.root_dir, 'app', 'config', 'db'))
        self.db_path = os.path.join(self.root_dir, 'app', 'config', 'db', 'crafty.sqlite')
        self.serverjar_cache = os.path.join(self.config_dir, 'serverjars.json')
        self.passhasher = PasswordHasher()
        self.exiting = False

    def check_file_perms(self, path):
        try:
            fp = open(path, "r").close()
            logger.info("{} is readable".format(path))
            return True
        except PermissionError:
            return False

    def is_file_older_than_x_days(self, file, days=1):
        if self.check_file_exists(file):
            file_time = os.path.getmtime(file)
            # Check against 24 hours
            if (time.time() - file_time) / 3600 > 24 * days:
                return True
            else:
                return False
        logger.error("{} does not exits".format(file))
        return False

    def get_setting(self, key, default_return=False):

        try:
            with open(self.settings_file, "r") as f:
                data = json.load(f)

            if key in data.keys():
                return data.get(key)

            else:
                logger.error("Config File Error: setting {} does not exist".format(key))
                console.error("Config File Error: setting {} does not exist".format(key))
                return default_return

        except Exception as e:
            logger.critical("Config File Error: Unable to read {} due to {}".format(self.settings_file, e))
            console.critical("Config File Error: Unable to read {} due to {}".format(self.settings_file, e))

        return default_return

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

    @staticmethod
    def get_announcements():
        r = requests.get('https://craftycontrol.com/notify.json', timeout=2)
        data = '[{"id":"1","date":"Unknown","title":"Error getting Announcements","desc":"Error getting ' \
               'Announcements","link":""}] '

        if r.status_code in [200, 201]:
            try:
                data = json.loads(r.content)
            except:
                pass

        return data


    def get_version_string(self):

        version_data = self.get_version()
        # set some defaults if we don't get version_data from our helper
        version = "{}.{}.{}".format(version_data.get('major', '?'),
                                    version_data.get('minor', '?'),
                                    version_data.get('sub', '?'))
        return str(version)

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

    def log_colors(self, line):
        # our regex replacements
        # note these are in a tuple

        user_keywords = self.get_setting('keywords')

        replacements = [
            (r'(\[.+?/INFO\])', r'<span class="mc-log-info">\1</span>'),
            (r'(\[.+?/WARN\])', r'<span class="mc-log-warn">\1</span>'),
            (r'(\[.+?/ERROR\])', r'<span class="mc-log-error">\1</span>'),
            (r'(\w+?\[/\d+?\.\d+?\.\d+?\.\d+?\:\d+?\])', r'<span class="mc-log-keyword">\1</span>'),
            (r'\[(\d\d:\d\d:\d\d)\]', r'<span class="mc-log-time">[\1]</span>'),
        ]

        # highlight users keywords
        for keyword in user_keywords:
            search_replace = (r'({})'.format(keyword), r'<span class="mc-log-keyword">\1</span>')
            replacements.append(search_replace)

        for old, new in replacements:
            line = re.sub(old, new, line, flags=re.IGNORECASE)

        return line

    def tail_file(self, file_name, number_lines=20):
        if not self.check_file_exists(file_name):
            logger.warning("Unable to find file to tail: {}".format(file_name))
            return ["Unable to find file to tail: {}".format(file_name)]

        # length of lines is X char here
        avg_line_length = 255

        # create our buffer number - number of lines * avg_line_length
        line_buffer = number_lines * avg_line_length

        # open our file
        with open(file_name, 'r') as f:

            # seek
            f.seek(0, 2)

            # get file size
            fsize = f.tell()

            # set pos @ last n chars (buffer from above = number of lines * avg_line_length)
            f.seek(max(fsize-line_buffer, 0), 0)

            # read file til the end
            try:
                lines = f.readlines()

            except Exception as e:
                logger.warning('Unable to read a line in the file:{} - due to error: {}'.format(file_name, e))
                pass

        # now we are done getting the lines, let's return it
        return lines

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
        session_log_file = os.path.join(os.path.curdir, 'logs', 'session.log')

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
            os.remove(session_log_file)
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
                console.critical("Another Crafty Controller agent seems to be running...\npid: {} \nstarted on: {}".format(pid, started))
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
        return str(uuid.uuid4())

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
        cert.set_serial_number(random.randint(1,255))
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)
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

    @staticmethod
    def is_os_windows():
        if os.name == 'nt':
            return True
        else:
            return False

    def find_default_password(self):
        default_file = os.path.join(self.root_dir, "default.json")
        data = {}

        if self.check_file_exists(default_file):
            with open(default_file, 'r') as f:
                data = json.load(f)

            del_json = helper.get_setting('delete_default_json')

            if del_json:
                os.remove(default_file)

        return data



helper = Helpers()
