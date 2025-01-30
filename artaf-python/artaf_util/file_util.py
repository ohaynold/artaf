"""Helper functions for file handling"""

import os
from contextlib import contextmanager


@contextmanager
def safe_open_write(file, mode, *args, new_file_suffix="~"):
    """
    Open a file for writing so that the entire write operation succeeds atomically or the file
    does not get written at all. This is accomplished by writing first to a file under a
    temporary name and then renaming that file to the intended filename once it's safely closed.
    :param file:
    :param mode:
    :param new_file_suffix:
    :param args:
    """
    if mode[0] not in ["w", "x"]:
        raise IOError("safe_open_write only works for creating or overwriting a new file")
    with open(file + new_file_suffix, mode, # pylint: disable=unspecified-encoding
              *args) as handle:
        try:
            yield handle
        except Exception as e:
            os.unlink(file + new_file_suffix)
            raise e
    os.rename(file + new_file_suffix, file)
