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
import ctypes
from datetime import datetime
from socket import gethostname
from contextlib import suppress
from requests import get

from app.classes.web.websocket_helper import websocket_helper
from app.classes.shared.console import console
from app.classes.shared.file_helpers import file_helper

logger = logging.getLogger(__name__)

try:
    import requests
    from OpenSSL import crypto
    from argon2 import PasswordHasher

except ModuleNotFoundError as err:
    logger.critical(f"Import Error: Unable to load {err.name} module", exc_info=True)
    console.critical(f"Import Error: Unable to load {err.name} module")
    sys.exit(1)

class Helpers:
    allowed_quotes = [
        "\"",
        "'",
        "`"
     ]

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
            open(path, "r", encoding='utf-8').close()
            logger.info(f"{path} is readable")
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
        logger.error(f"{file} does not exist")
        return True

    def get_servers_root_dir(self):
        return self.servers_dir

    @staticmethod
    def check_internet():
        try:
            requests.get('https://google.com', timeout=1)
            return True
        except Exception:
            return False

    @staticmethod
    def check_port(server_port):
        try:
            ip = get('https://api.ipify.org').content.decode('utf8')
        except:
            ip = 'google.com'
        a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        a_socket.settimeout(20.0)

        location = (ip, server_port)
        result_of_check = a_socket.connect_ex(location)

        a_socket.close()

        if result_of_check == 0:
            return True
        else:
            return False

    @staticmethod
    def check_server_conn(server_port):
        a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        a_socket.settimeout(10.0)
        ip = '127.0.0.1'

        location = (ip, server_port)
        result_of_check = a_socket.connect_ex(location)
        a_socket.close()

        if result_of_check == 0:
            return True
        else:
            return False

    @staticmethod
    def cmdparse(cmd_in):
        # Parse a string into arguments
        cmd_out = [] # "argv" output array
        ci = -1      # command index - pointer to the argument we're building in cmd_out
        np = True    # whether we're creating a new argument/parameter
        esc = False  # whether an escape character was encountered
        stch = None  # if we're dealing with a quote, save the quote type here.  Nested quotes to be dealt with by the command
        for c in cmd_in: # for character in string
            if np: # if set, begin a new argument and increment the command index.  Continue the loop.
                if c == ' ':
                    continue
                else:
                    ci += 1
                    cmd_out.append("")
                    np = False
            if esc: # if we encountered an escape character on the last loop, append this char regardless of what it is
                if c not in Helpers.allowed_quotes:
                    cmd_out[ci] += '\\'
                cmd_out[ci] += c
                esc = False
            else:
                if c == '\\': # if the current character is an escape character, set the esc flag and continue to next loop
                    esc = True
                elif c == ' ' and stch is None: # if we encounter a space and are not dealing with a quote,
                                                # set the new argument flag and continue to next loop
                    np = True
                elif c == stch: # if we encounter the character that matches our start quote, end the quote and continue to next loop
                    stch = None
                elif stch is None and (c in Helpers.allowed_quotes): # if we're not in the middle of a quote and we get a quotable character,
                                                                     # start a quote and proceed to the next loop
                    stch = c
                else: # else, just store the character in the current arg
                    cmd_out[ci] += c
        return cmd_out

    def get_setting(self, key, default_return=False):

        try:
            with open(self.settings_file, "r", encoding='utf-8') as f:
                data = json.load(f)

            if key in data.keys():
                return data.get(key)

            else:
                logger.error(f"Config File Error: setting {key} does not exist")
                console.error(f"Config File Error: setting {key} does not exist")
                return default_return

        except Exception as e:
            logger.critical(f"Config File Error: Unable to read {self.settings_file} due to {e}")
            console.critical(f"Config File Error: Unable to read {self.settings_file} due to {e}")

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
            with open(os.path.join(self.config_dir, 'version.json'), 'r', encoding='utf-8') as f:
                version_data = json.load(f)

        except Exception as e:
            console.critical(f"Unable to get version data! \n{e}")

        return version_data

    @staticmethod
    def get_announcements():
        r = requests.get('https://craftycontrol.com/notify.json', timeout=2)
        data = '[{"id":"1","date":"Unknown","title":"Error getting Announcements","desc":"Error getting ' \
               'Announcements","link":""}] '

        if r.status_code in [200, 201]:
            try:
                data = json.loads(r.content)
            except Exception as e:
                logger.error(f"Failed to load json content with error: {e}")

        return data


    def get_version_string(self):

        version_data = self.get_version()
        major = version_data.get('major', '?')
        minor = version_data.get('minor', '?')
        sub = version_data.get('sub', '?')
        meta = version_data.get('meta', '?')

        # set some defaults if we don't get version_data from our helper
        version = f"{major}.{minor}.{sub}-{meta}"
        return str(version)

    def encode_pass(self, password):
        return self.passhasher.hash(password)

    def verify_pass(self, password, currenthash):
        try:
            self.passhasher.verify(currenthash, password)
            return True
        except:
            return False

    def log_colors(self, line):
        # our regex replacements
        # note these are in a tuple

        user_keywords = self.get_setting('keywords')

        replacements = [
            (r'(\[.+?/INFO\])', r'<span class="mc-log-info">\1</span>'),
            (r'(\[.+?/WARN\])', r'<span class="mc-log-warn">\1</span>'),
            (r'(\[.+?/ERROR\])', r'<span class="mc-log-error">\1</span>'),
            (r'(\[.+?/FATAL\])', r'<span class="mc-log-fatal">\1</span>'),
            (r'(\w+?\[/\d+?\.\d+?\.\d+?\.\d+?\:\d+?\])', r'<span class="mc-log-keyword">\1</span>'),
            (r'\[(\d\d:\d\d:\d\d)\]', r'<span class="mc-log-time">[\1]</span>'),
            (r'(\[.+? INFO\])', r'<span class="mc-log-info">\1</span>'),
            (r'(\[.+? WARN\])', r'<span class="mc-log-warn">\1</span>'),
            (r'(\[.+? ERROR\])', r'<span class="mc-log-error">\1</span>'),
            (r'(\[.+? FATAL\])', r'<span class="mc-log-fatal">\1</span>')
        ]

        # highlight users keywords
        for keyword in user_keywords:
            # pylint: disable=consider-using-f-string
            search_replace = (r'({})'.format(keyword), r'<span class="mc-log-keyword">\1</span>')
            replacements.append(search_replace)

        for old, new in replacements:
            line = re.sub(old, new, line, flags=re.IGNORECASE)

        return line


    def validate_traversal(self, base_path, filename):
        logger.debug(f"Validating traversal (\"{base_path}\", \"{filename}\")")
        base = pathlib.Path(base_path).resolve()
        file = pathlib.Path(filename)
        fileabs = base.joinpath(file).resolve()
        cp = pathlib.Path(os.path.commonpath([base, fileabs]))
        if base == cp:
            return fileabs
        else:
            raise ValueError("Path traversal detected")


    def tail_file(self, file_name, number_lines=20):
        if not self.check_file_exists(file_name):
            logger.warning(f"Unable to find file to tail: {file_name}")
            return [f"Unable to find file to tail: {file_name}"]

        # length of lines is X char here
        avg_line_length = 255

        # create our buffer number - number of lines * avg_line_length
        line_buffer = number_lines * avg_line_length

        # open our file
        with open(file_name, 'r', encoding='utf-8') as f:

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
                logger.warning(f'Unable to read a line in the file:{file_name} - due to error: {e}')

        # now we are done getting the lines, let's return it
        return lines

    @staticmethod
    def check_writeable(path: str):
        filename = os.path.join(path, "tempfile.txt")
        try:
            open(filename, "w", encoding='utf-8').close()
            os.remove(filename)

            logger.info(f"{filename} is writable")
            return True

        except Exception as e:
            logger.critical(f"Unable to write to {path} - Error: {e}")
            return False

    def checkRoot(self):
        if self.is_os_windows():
            if ctypes.windll.shell32.IsUserAnAdmin() == 1:
                return True
            else:
                return False
        else:
            if os.geteuid() == 0:
                return True
            else:
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
                for i in enumerate(zip_ref.filelist):
                    if len(zip_ref.filelist) > 1 or not zip_ref.filelist[i].filename.endswith('/'):
                        break

                full_root_path = tempDir

                for item in os.listdir(full_root_path):
                    try:
                        file_helper.move_dir(os.path.join(full_root_path, item), os.path.join(new_dir, item))
                    except Exception as ex:
                        logger.error(f'ERROR IN ZIP IMPORT: {ex}')
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
            logger.critical(f"Unable to write to {self.root_dir} directory!")
            sys.exit(1)

        # ensure the log directory is there
        try:
            with suppress(FileExistsError):
                os.makedirs(os.path.join(self.root_dir, 'logs'))
        except Exception as e:
            console.error(f"Failed to make logs directory with error: {e} ")

        # ensure the log file is there
        try:
            open(log_file, 'a', encoding='utf-8').close()
        except Exception as e:
            console.critical(f"Unable to open log file! {e}")
            sys.exit(1)

        # del any old session.lock file as this is a new session
        try:
            os.remove(session_log_file)
        except Exception as e:
            logger.error(f"Deleting Session.lock failed with error: {e}")

    @staticmethod
    def get_time_as_string():
        now = datetime.now()
        return now.strftime("%m/%d/%Y, %H:%M:%S")

    @staticmethod
    def check_file_exists(path: str):
        logger.debug(f'Looking for path: {path}')

        if os.path.exists(path) and os.path.isfile(path):
            logger.debug(f'Found path: {path}')
            return True
        else:
            return False

    @staticmethod
    def human_readable_file_size(num: int, suffix='B'):
        for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
            if abs(num) < 1024.0:
            # pylint: disable=consider-using-f-string
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
            # pylint: disable=consider-using-f-string
        return "%.1f%s%s" % (num, 'Y', suffix)

    @staticmethod
    def check_path_exists(path: str):
        if not path:
            return False
        logger.debug(f'Looking for path: {path}')

        if os.path.exists(path):
            logger.debug(f'Found path: {path}')
            return True
        else:
            return False

    @staticmethod
    def get_file_contents(path: str, lines=100):

        contents = ''

        if os.path.exists(path) and os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for line in (f.readlines() [-lines:]):
                        contents = contents + line

                return contents

            except Exception as e:
                logger.error(f"Unable to read file: {path}. \n Error: {e}")
                return False
        else:
            logger.error(f"Unable to read file: {path}. File not found, or isn't a file.")
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
                console.critical(f"Another Crafty Controller agent seems to be running...\npid: {pid} \nstarted on: {started}")
            except Exception as e:
                logger.error(f"Failed to locate existing session.lock with error: {e} ")
                console.error(f"Failed to locate existing session.lock with error: {e} ")

            sys.exit(1)

        pid = os.getpid()
        now = datetime.now()

        session_data = {
            'pid': pid,
            'started': now.strftime("%d-%m-%Y, %H:%M:%S")
            }
        with open(self.session_file, 'w', encoding='utf-8') as f:
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
    def base64_encode_string(fun_str: str):
        s_bytes = str(fun_str).encode('utf-8')
        b64_bytes = base64.encodebytes(s_bytes)
        return b64_bytes.decode('utf-8')

    @staticmethod
    def base64_decode_string(fun_str: str):
        s_bytes = str(fun_str).encode('utf-8')
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
            logger.debug(f"Created Directory : {path}")

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

        logger.info(f"SSL Cert File is set to: {cert_file}")
        logger.info(f"SSL Key File is set to: {key_file}")

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

        f = open(cert_file, "w", encoding='utf-8')
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode())
        f.close()

        f = open(key_file, "w", encoding='utf-8')
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

    @staticmethod
    def wtol_path(w_path):
        l_path = w_path.replace('\\', '/')
        return l_path

    @staticmethod
    def ltow_path(l_path):
        w_path = l_path.replace('/', '\\')
        return w_path

    @staticmethod
    def get_os_understandable_path(path):
        return os.path.normpath(path)

    def find_default_password(self):
        default_file = os.path.join(self.root_dir, "default.json")
        data = {}

        if self.check_file_exists(default_file):
            with open(default_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            del_json = helper.get_setting('delete_default_json')

            if del_json:
                os.remove(default_file)

        return data

    @staticmethod
    def generate_tree(folder, output=""):
        dir_list = []
        unsorted_files = []
        file_list = os.listdir(folder)
        for item in file_list:
            if os.path.isdir(os.path.join(folder, item)):
                dir_list.append(item)
            else:
                unsorted_files.append(item)
        file_list = sorted(dir_list, key=str.casefold) + sorted(unsorted_files, key=str.casefold)
        for raw_filename in file_list:
            filename = html.escape(raw_filename)
            rel = os.path.join(folder, raw_filename)
            dpath = os.path.join(folder, filename)
            if os.path.isdir(rel):
                output += \
                    f"""<li class="tree-item" data-path="{dpath}">
                    \n<div id="{dpath}" data-path="{dpath}" data-name="{filename}" class="tree-caret tree-ctx-item tree-folder">
                    <span id="{dpath}span" class="files-tree-title" data-path="{dpath}" data-name="{filename}" onclick="getDirView(event)">
                      <i class="far fa-folder"></i>
                      <i class="far fa-folder-open"></i>
                      {filename}
                      </span>
                    </div><li>
                    \n"""\

            else:
                if filename != "crafty_managed.txt":
                    output += f"""<li
                    class="tree-nested d-block tree-ctx-item tree-file"
                    data-path="{dpath}"
                    data-name="{filename}"
                    onclick="clickOnFile(event)"><span style="margin-right: 6px;"><i class="far fa-file"></i></span>{filename}</li>"""
        return output

    @staticmethod
    def generate_dir(folder, output=""):
        dir_list = []
        unsorted_files = []
        file_list = os.listdir(folder)
        for item in file_list:
            if os.path.isdir(os.path.join(folder, item)):
                dir_list.append(item)
            else:
                unsorted_files.append(item)
        file_list = sorted(dir_list, key=str.casefold) + sorted(unsorted_files, key=str.casefold)
        output += \
    f"""<ul class="tree-nested d-block" id="{folder}ul">"""\

        for raw_filename in file_list:
            filename = html.escape(raw_filename)
            dpath = os.path.join(folder, filename)
            rel = os.path.join(folder, raw_filename)
            if os.path.isdir(rel):
                output += \
                    f"""<li class="tree-item" data-path="{dpath}">
                    \n<div id="{dpath}" data-path="{dpath}" data-name="{filename}" class="tree-caret tree-ctx-item tree-folder">
                    <span id="{dpath}span" class="files-tree-title" data-path="{dpath}" data-name="{filename}" onclick="getDirView(event)">
                      <i class="far fa-folder"></i>
                      <i class="far fa-folder-open"></i>
                      {filename}
                      </span>
                    </div><li>"""\

            else:
                if filename != "crafty_managed.txt":
                    output += f"""<li
                    class="tree-nested d-block tree-ctx-item tree-file"
                    data-path="{dpath}"
                    data-name="{filename}"
                    onclick="clickOnFile(event)"><span style="margin-right: 6px;"><i class="far fa-file"></i></span>{filename}</li>"""
        output += '</ul>\n'
        return output

    @staticmethod
    def generate_zip_tree(folder, output=""):
        file_list = os.listdir(folder)
        file_list = sorted(file_list, key=str.casefold)
        output += \
    f"""<ul class="tree-nested d-block" id="{folder}ul">"""\

        for raw_filename in file_list:
            filename = html.escape(raw_filename)
            rel = os.path.join(folder, raw_filename)
            dpath = os.path.join(folder, filename)
            if os.path.isdir(rel):
                output += \
                    f"""<li class="tree-item" data-path="{dpath}">
                    \n<div id="{dpath}" data-path="{dpath}" data-name="{filename}" class="tree-caret tree-ctx-item tree-folder">
                    <input type="radio" name="root_path" value="{dpath}">
                    <span id="{dpath}span" class="files-tree-title" data-path="{dpath}" data-name="{filename}" onclick="getDirView(event)">
                      <i class="far fa-folder"></i>
                      <i class="far fa-folder-open"></i>
                      {filename}
                      </span>
                    </input></div><li>
                    \n"""\

        return output

    @staticmethod
    def generate_zip_dir(folder, output=""):
        file_list = os.listdir(folder)
        file_list = sorted(file_list, key=str.casefold)
        output += \
    f"""<ul class="tree-nested d-block" id="{folder}ul">"""\

        for raw_filename in file_list:
            filename = html.escape(raw_filename)
            rel = os.path.join(folder, raw_filename)
            dpath = os.path.join(folder, filename)
            if os.path.isdir(rel):
                output += \
                    f"""<li class="tree-item" data-path="{dpath}">
                    \n<div id="{dpath}" data-path="{dpath}" data-name="{filename}" class="tree-caret tree-ctx-item tree-folder">
                    <input type="radio" name="root_path" value="{dpath}">
                    <span id="{dpath}span" class="files-tree-title" data-path="{dpath}" data-name="{filename}" onclick="getDirView(event)">
                      <i class="far fa-folder"></i>
                      <i class="far fa-folder-open"></i>
                      {filename}
                      </span>
                    </input></div><li>"""\

        return output

    @staticmethod
    def unzipServer(zip_path, user_id):
        if helper.check_file_perms(zip_path):
            tempDir = tempfile.mkdtemp()
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                #extracts archive to temp directory
                zip_ref.extractall(tempDir)
            if user_id:
                websocket_helper.broadcast_user(user_id, 'send_temp_path',{
                'path': tempDir
                })
    @staticmethod
    def backup_select(path, user_id):
        if user_id:
            websocket_helper.broadcast_user(user_id, 'send_temp_path',{
            'path': path
        })

    @staticmethod
    def unzip_backup_archive(backup_path, zip_name):
        zip_path = os.path.join(backup_path, zip_name)
        if helper.check_file_perms(zip_path):
            tempDir = tempfile.mkdtemp()
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                #extracts archive to temp directory
                zip_ref.extractall(tempDir)
            return tempDir
        else:
            return False

    @staticmethod
    def in_path(parent_path, child_path):
        # Smooth out relative path names, note: if you are concerned about symbolic links, you should use os.path.realpath too
        parent_path = os.path.abspath(parent_path)
        child_path = os.path.abspath(child_path)

        # Compare the common path of the parent and child path with the common path of just the parent path.
        # Using the commonpath method on just the parent path will regularise the path name in the same way
        # as the comparison that deals with both paths, removing any trailing path separator
        return os.path.commonpath([parent_path]) == os.path.commonpath([parent_path, child_path])

    @staticmethod
    def in_path_old(x, y):
        return os.path.abspath(y).__contains__(os.path.abspath(x))

    @staticmethod
    def copy_files(source, dest):
        if os.path.isfile(source):
            file_helper.copy_file(source, dest)
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
