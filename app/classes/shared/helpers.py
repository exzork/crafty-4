import os
import re
import sys
import json
import tempfile
import time
import uuid
import string
import base64
import socket
import random
import logging
import html
import zipfile
import pathlib
import shutil
from requests import get

from datetime import datetime
from socket import gethostname

from app.classes.shared.console import console

logger = logging.getLogger(__name__)

try:
    import requests
    from OpenSSL import crypto
    from argon2 import PasswordHasher

except ModuleNotFoundError as e:
    logger.critical("Import Error: Unable to load {} module".format(e.name), exc_info=True)
    console.critical("Import Error: Unable to load {} module".format(e.name))
    sys.exit(1)

class Helpers:

    def __init__(self):
        self.root_dir = os.path.abspath(os.path.curdir)
        self.config_dir = os.path.join(self.root_dir, 'app', 'config')
        self.webroot = os.path.join(self.root_dir, 'app', 'frontend')
        self.servers_dir = os.path.join(self.root_dir, 'servers')
        self.backup_path = os.path.join(self.root_dir, 'backups')
        self.migration_dir = os.path.join(self.root_dir, 'app', 'migrations')

        self.session_file = os.path.join(self.root_dir, 'app', 'config', 'session.lock')
        self.settings_file = os.path.join(self.root_dir, 'app', 'config', 'config.json')

        self.ensure_dir_exists(os.path.join(self.root_dir, 'app', 'config', 'db'))
        self.db_path = os.path.join(self.root_dir, 'app', 'config', 'db', 'crafty.sqlite')
        self.serverjar_cache = os.path.join(self.config_dir, 'serverjars.json')
        self.credits_cache = os.path.join(self.config_dir, 'credits.json')
        self.passhasher = PasswordHasher()
        self.exiting = False

    def float_to_string(self, gbs: int):
        s = str(float(gbs) * 1000).rstrip("0").rstrip(".")
        return s

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
        logger.error("{} does not exist".format(file))
        return True

    @staticmethod
    def check_internet():
        try:
            requests.get('https://google.com', timeout=1)
            return True
        except Exception as err:
            return False

    @staticmethod
    def check_port(server_port):
        try:
            host_public = get('https://api.ipify.org').text
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            result = sock.connect_ex((host_public ,server_port))
            sock.close()
            if result == 0:
                return True
            else:
                return False
        except Exception as err:
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
        version = "{}.{}.{}-{}".format(version_data.get('major', '?'),
                                    version_data.get('minor', '?'),
                                    version_data.get('sub', '?'),
                                    version_data.get('meta', '?'))
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
            (r'(\[.+? INFO\])', r'<span class="mc-log-info">\1</span>'),
            (r'(\[.+? WARN\])', r'<span class="mc-log-warn">\1</span>'),
            (r'(\[.+? ERROR\])', r'<span class="mc-log-error">\1</span>')
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

    def unzipFile(self, zip_path):
        new_dir_list = zip_path.split('/')
        new_dir = ''
        for i in range(len(new_dir_list)-1):
            if i == 0:
                new_dir += new_dir_list[i]
            else:
                new_dir += '/'+new_dir_list[i]

        if helper.check_file_perms(zip_path) and os.path.isfile(zip_path):
            helper.ensure_dir_exists(new_dir)
            tempDir = tempfile.mkdtemp()
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(tempDir)
                for i in range(len(zip_ref.filelist)):
                    if len(zip_ref.filelist) > 1 or not zip_ref.filelist[i].filename.endswith('/'):
                        test = zip_ref.filelist[i].filename
                        break
                path_list = test.split('/')
                root_path = path_list[0]
                '''
                if len(path_list) > 1:
                    for i in range(len(path_list) - 2):
                        root_path = os.path.join(root_path, path_list[i + 1])
'''
                full_root_path = tempDir

                for item in os.listdir(full_root_path):
                    try:
                        shutil.move(os.path.join(full_root_path, item), os.path.join(new_dir, item))
                    except Exception as ex:
                        logger.error('ERROR IN ZIP IMPORT: {}'.format(ex))
            except Exception as ex:
                print(ex)
        else:
            return "false"
        return

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
    def check_path_exists(path: str):
        if not path:
            return False
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
    def list_dir_by_date(path: str, reverse=False):
        return [str(p) for p in sorted(pathlib.Path(path).iterdir(), key=os.path.getmtime, reverse=reverse)]

    def get_human_readable_files_sizes(self, paths: list):
        sizes = []
        for p in paths:
            sizes.append({
                "path": p,
                "size": self.human_readable_file_size(os.stat(p).st_size)
            })
        return sizes

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

    @staticmethod
    def generate_tree(folder, output=""):
        for raw_filename in os.listdir(folder):
            filename = html.escape(raw_filename)
            rel = os.path.join(folder, raw_filename)
            if os.path.isdir(rel):
                output += \
                    """<li class="tree-item" data-path="{}">
                    \n<div data-path="{}" data-name="{}" class="tree-caret tree-ctx-item tree-folder">
                      <i class="far fa-folder"></i>
                      <i class="far fa-folder-open"></i>
                      {}
                    </div>
                    \n<ul class="tree-nested">"""\
                        .format(os.path.join(folder, filename), os.path.join(folder, filename), filename, filename)

                output += helper.generate_tree(rel)
                output += '</ul>\n</li>'
            else:
                output += """<li
                class="tree-item tree-ctx-item tree-file"
                data-path="{}"
                data-name="{}"
                onclick="clickOnFile(event)"><span style="margin-right: 6px;"><i class="far fa-file"></i></span>{}</li>""".format(os.path.join(folder, filename), filename, filename)
        return output

    @staticmethod
    def in_path(parent_path, child_path):
        # Smooth out relative path names, note: if you are concerned about symbolic links, you should use os.path.realpath too
        parent_path = os.path.abspath(parent_path)
        child_path = os.path.abspath(child_path)

        # Compare the common path of the parent and child path with the common path of just the parent path. Using the commonpath method on just the parent path will regularise the path name in the same way as the comparison that deals with both paths, removing any trailing path separator
        return os.path.commonpath([parent_path]) == os.path.commonpath([parent_path, child_path])

    @staticmethod
    def in_path_old(x, y):
        return os.path.abspath(y).__contains__(os.path.abspath(x))

    @staticmethod
    def copy_files(source, dest):
        if os.path.isfile(source):
            shutil.copyfile(source, dest)
            logger.info("Copying jar %s to %s", source, dest)
        else:
            logger.info("Source jar does not exist.")

    @staticmethod
    def download_file(executable_url, jar_path):
        try:
            r = requests.get(executable_url, timeout=5)
        except Exception as ex:
            logger.error("Could not download executable: %s", ex)
            return False
        if r.status_code != 200:
            logger.error("Unable to download file from %s", executable_url)
            return False

        try:
            open(jar_path, "wb").write(r.content)
        except Exception as e:
            logger.error("Unable to finish executable download. Error: %s", e)
            return False
        return True


    @staticmethod
    def remove_prefix(text, prefix):
        if text.startswith(prefix):
            return text[len(prefix):]
        return text

helper = Helpers()
