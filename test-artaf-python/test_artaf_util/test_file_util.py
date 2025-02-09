"""Test artaf_util.file_util"""
import os.path
import tempfile
import zipfile
from contextlib import contextmanager

import pytest

import artaf_util


@contextmanager
def make_temp_directory():
    """Make a temporary directory and delete it"""
    temp_dir = tempfile.mkdtemp()
    try:
        yield temp_dir
    finally:
        for f in os.listdir(temp_dir):
            os.unlink(os.path.join(temp_dir, f))
        # On some operating systems, we can't delete this manually, but it will be taken care
        # of for us
        try:
            os.unlink(temp_dir)
        except PermissionError:
            pass


class TestSafeOpenWrite:
    """Test artaf_util.safe_open_write()"""

    def test_successful_write(self):
        """Test a successful write operation"""
        with make_temp_directory() as temp_dir:
            test_content = "Hello world!\n"
            temp_file_name = os.path.join(temp_dir, "testfile.txt")
            with artaf_util.safe_open_write(temp_file_name, "w") as out_file:
                out_file.write(test_content)
            with open(temp_file_name, "r", encoding="ascii") as in_file:
                assert in_file.read() == test_content

    def test_failed_write(self):
        """Test an unsuccessful write operation interrupted by an exception"""
        with make_temp_directory() as temp_dir:
            test_content = "Hello world!\n"
            temp_file_name = os.path.join(temp_dir, "testfile.txt")
            with open(temp_file_name, "w", encoding="ascii") as out_file:
                out_file.write(test_content)
            try:
                with artaf_util.safe_open_write(temp_file_name, "w", encoding="ascii") as out_file:
                    out_file.write("ERROR CONTENT")
                    # Something goes wrong
                    raise ValueError("Backing out...")
            except ValueError:
                pass
            # We should still have the original file content
            with open(temp_file_name, "r", encoding="ascii") as in_file:
                assert in_file.read() == test_content

    def test_failed_read(self):
        """Test that we can't read from a file safely opened for writing"""
        with make_temp_directory() as temp_dir:
            temp_file_name = os.path.join(temp_dir, "testfile.txt")
            with pytest.raises(IOError):
                with  artaf_util.safe_open_write(temp_file_name, "r", encoding="ascii") as in_file:
                    in_file.read()


class TestOpenCompressedZipWrite:
    """Test artaf_util.pen_compressed_text_zip_write"""

    def test_open_compressed_zip_write(self):
        """Test roundtrip for compressed text file"""
        test_content = "Hello world!\n"
        with make_temp_directory() as temp_dir:
            temp_file_name = os.path.join(temp_dir, "test.csv.zip")
            inner_file_name = "test.csv"
            with artaf_util.open_compressed_text_zip_write(temp_file_name, inner_file_name, "ascii",
                                                           zipfile.ZIP_DEFLATED) as out_file:
                out_file.write(test_content)
            with zipfile.ZipFile(temp_file_name, "r") as in_zip_file:
                the_bytes = in_zip_file.read(inner_file_name)
                assert the_bytes.decode("ascii") == test_content
