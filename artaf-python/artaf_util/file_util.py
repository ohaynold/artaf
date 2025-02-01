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
    # We pass on encoding arguments, but don't enforce them to keep the signature the same as
    # open()
    with open(file + new_file_suffix, mode, # pylint: disable=unspecified-encoding
              *args) as handle:
        failure = None
        try:
            # This works due to the @contextmanager decorator for this function
            yield handle
        # Intentionally catching all exceptions -- we'll clean up and then reraise, so this is in
        # practice a finally statement, except getting out of the with block first
        except Exception as e: # pylint: disable=broad-exception-caught
            failure = e
    if failure is None:
        os.rename(file + new_file_suffix, file)
    else:
        os.unlink(file + new_file_suffix)
        raise failure
