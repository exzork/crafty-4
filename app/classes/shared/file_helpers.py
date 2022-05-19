import os
import shutil
import logging
import pathlib
from zipfile import ZipFile, ZIP_DEFLATED

logger = logging.getLogger(__name__)


class FileHelpers:
    allowed_quotes = ['"', "'", "`"]

    @staticmethod
    def del_dirs(path):
        path = pathlib.Path(path)
        for sub in path.iterdir():
            if sub.is_dir():
                # Delete folder if it is a folder
                FileHelpers.del_dirs(sub)
            else:
                # Delete file if it is a file:
                sub.unlink()

        # This removes the top-level folder:
        path.rmdir()
        return True

    @staticmethod
    def del_file(path):
        path = pathlib.Path(path)
        try:
            logger.debug(f"Deleting file: {path}")
            # Remove the file
            os.remove(path)
            return True
        except FileNotFoundError:
            logger.error(f"Path specified is not a file or does not exist. {path}")
            return False

    @staticmethod
    def copy_dir(src_path, dest_path, dirs_exist_ok=False):
        # pylint: disable=unexpected-keyword-arg
        shutil.copytree(src_path, dest_path, dirs_exist_ok=dirs_exist_ok)

    @staticmethod
    def copy_file(src_path, dest_path):
        shutil.copy(src_path, dest_path)

    @staticmethod
    def move_dir(src_path, dest_path):
        FileHelpers.copy_dir(src_path, dest_path)
        FileHelpers.del_dirs(src_path)

    @staticmethod
    def move_file(src_path, dest_path):
        FileHelpers.copy_file(src_path, dest_path)
        FileHelpers.del_file(src_path)

    @staticmethod
    def make_archive(path_to_destination, path_to_zip):
        # create a ZipFile object
        path_to_destination += ".zip"
        with ZipFile(path_to_destination, "w") as zip_file:
            for root, _dirs, files in os.walk(path_to_zip, topdown=True):
                ziproot = path_to_zip
                for file in files:
                    try:
                        logger.info(f"backing up: {os.path.join(root, file)}")
                        if os.name == "nt":
                            zip_file.write(
                                os.path.join(root, file),
                                os.path.join(root.replace(ziproot, ""), file),
                            )
                        else:
                            zip_file.write(
                                os.path.join(root, file),
                                os.path.join(root.replace(ziproot, "/"), file),
                            )

                    except Exception as e:
                        logger.warning(
                            f"Error backing up: {os.path.join(root, file)}!"
                            f" - Error was: {e}"
                        )

        return True

    @staticmethod
    def make_compressed_archive(path_to_destination, path_to_zip):
        # create a ZipFile object
        path_to_destination += ".zip"
        with ZipFile(path_to_destination, "w", ZIP_DEFLATED) as zip_file:
            for root, _dirs, files in os.walk(path_to_zip, topdown=True):
                ziproot = path_to_zip
                for file in files:
                    try:
                        logger.info(f"backing up: {os.path.join(root, file)}")
                        if os.name == "nt":
                            zip_file.write(
                                os.path.join(root, file),
                                os.path.join(root.replace(ziproot, ""), file),
                            )
                        else:
                            zip_file.write(
                                os.path.join(root, file),
                                os.path.join(root.replace(ziproot, "/"), file),
                            )

                    except Exception as e:
                        logger.warning(
                            f"Error backing up: {os.path.join(root, file)}!"
                            f" - Error was: {e}"
                        )

        return True
