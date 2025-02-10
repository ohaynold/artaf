"""Helper functions for file handling"""

import io
import os
import zipfile
from contextlib import contextmanager


@contextmanager
def safe_open_write(file, mode, new_file_suffix="~", **kwargs):
    """
    Open a file for writing so that the entire write operation succeeds atomically or the file
    does not get written at all. This is accomplished by writing first to a file under a
    temporary name and then renaming that file to the intended filename once it's safely closed.
    :param file: File path
    :param mode: File mode, as in open, must be for writing
    :param new_file_suffix: Suffix for the temporary file
    :param kwargs: Any other parameters, such as encoding, passed to open()
    """
    if len(new_file_suffix) == 0:
        raise ValueError("Need a non-empty suffix for the temporary file")
    if mode[0] not in ["w", "x"]:
        raise IOError("safe_open_write only works for creating or overwriting a new file")
    # We pass on encoding arguments, but don't enforce them to keep the signature the same as
    # open()
    with open(file + new_file_suffix, mode,  # pylint: disable=unspecified-encoding
              **kwargs) as handle:
        failure = None
        try:
            # This works due to the @contextmanager decorator for this function
            yield handle
        # Intentionally catching all exceptions -- we'll clean up and then reraise, so this is in
        # practice a finally statement, except getting out of the with block first
        except Exception as e:  # pylint: disable=broad-exception-caught
            failure = e
    if failure is None:
        os.rename(file + new_file_suffix, file)
    else:
        os.unlink(file + new_file_suffix)
        raise failure


@contextmanager
def safe_open_compressed_text_zip_write(compressed_path, inner_file_name, encoding, compression,
                                        new_file_suffix="~"):
    """
    Open a compressed ZIP file containing exactly one text file for writing. Writing succeeds or
    fails atomically, i.e., the output file only replaces a previous file of the same name
    after successful completion of all write operations and closing.
    :param compressed_path: Path of the compressed ZIP file to be created
    :param inner_file_name: Name of the inner file within the ZIP file
    :param encoding: The encoding of the text to be written
    :param compression: One of the compression constants of the zipfile module, e.g.,
    zipfile.ZIP_DEFLATED
    :param new_file_suffix: Suffix for temporary newly created file
    """
    if len(new_file_suffix) == 0:
        raise ValueError("Need a non-empty suffix for the temporary file")
    with (
        zipfile.ZipFile(compressed_path + new_file_suffix, "w", compression) as out_zip_file,
        out_zip_file.open(inner_file_name, "w", force_zip64=True) as out_bin_file,
        io.TextIOWrapper(out_bin_file, encoding=encoding, newline="\n") as out_file
    ):
        failure = None
        try:
            yield out_file
        # Intentionally catching all exceptions -- we'll clean up and then reraise, so this is in
        # practice a finally statement, except getting out of the with block first
        except Exception as e:  # pylint: disable=broad-exception-caught
            failure = e
    if failure is None:
        os.rename(compressed_path + new_file_suffix, compressed_path)
    else:
        os.unlink(compressed_path + new_file_suffix)
        raise failure
