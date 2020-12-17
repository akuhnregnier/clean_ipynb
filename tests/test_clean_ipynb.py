# -*- coding: utf-8 -*-
import shutil
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

import pytest

from clean_ipynb import clean_ipynb, clean_py


@pytest.mark.parametrize("mode", ("cli", "module"))
@pytest.mark.parametrize(
    "filetype,keep_output,raw,known_good",
    [
        ("py", False, "raw_python.py", "clean_python.py"),
        ("ipynb", False, "raw_python_notebook.ipynb", "clean_python_notebook.ipynb"),
        (
            "ipynb",
            True,
            "raw_python_notebook.ipynb",
            "clean_python_notebook_with_output.ipynb",
        ),
    ],
)
def test_expected(filetype, mode, keep_output, raw, known_good):
    """Test the cleaning of a single Python script or notebook."""
    fixture_dir = Path(__file__).resolve().parent / "fixtures"
    raw_file = fixture_dir / raw

    # Use a temporary file to contain the cleaned notebook.
    # with NamedTemporaryFile(suffix=raw_file.suffix) as temp_cleaned_file:
    # temp_clean_filename = temp_cleaned_file.name
    with TemporaryDirectory(suffix="clean_ipynb") as temp_dir:
        temp_clean_filename = Path(temp_dir) / raw
        # Copy the original 'dirty' notebook for later in-place cleaning.
        shutil.copy(raw_file, temp_clean_filename)
        # Record the initial number of files in the directory.
        orig_n_files = len(list(Path(temp_dir).iterdir()))

        # Clean the notebook.
        if mode == "module":
            if raw_file.suffix == ".ipynb":
                clean_ipynb(temp_clean_filename, keep_output=keep_output)
            elif raw_file.suffix == ".py":
                clean_py(temp_clean_filename)
            else:
                raise ValueError(f"Unsupported suffix '{raw_file.suffix}'.")
        elif mode == "cli":
            # Make sure that the command ran successfully.
            assert not run(
                (
                    "clean_ipynb",
                    *(("--keep-output",) if keep_output else ()),
                    temp_clean_filename,
                )
            ).returncode
        else:
            raise ValueError(f"Unsupported mode: '{mode}'.")
        # Read the contents of the cleaned notebook.
        with open(temp_clean_filename) as f:
            cleaned = f.read()

        # Ensure that no temporary files are left over.
        new_n_files = len(list(Path(temp_dir).iterdir()))
        assert new_n_files == orig_n_files

    # Compare the known good notebook to the above.
    with open(fixture_dir / known_good) as f:
        target_clean = f.read()

    assert target_clean == cleaned
