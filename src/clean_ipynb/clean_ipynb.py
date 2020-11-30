# -*- coding: utf-8 -*-
import re
from pathlib import Path

from autoflake import fix_code
from black import FileMode, NothingChanged, format_file_contents
from isort import code
from jupytext.cli import jupytext

__all__ = ("clean_ipynb", "clean_py", "clean_python_code")


def clean_python_code(python_code, isort=True, black=True, autoflake=True):
    """Clean Python code."""
    # Temporarily comment out IPython %magic to avoid Black errors.
    python_code = re.sub("^%", "##%##", python_code, flags=re.M)

    # Run source code string through autoflake, isort, and black.
    if autoflake:
        # Programmatic autoflake.
        python_code = fix_code(
            python_code,
            expand_star_imports=True,
            remove_all_unused_imports=True,
            remove_duplicate_keys=True,
            remove_unused_variables=True,
        )

    if isort:
        python_code = code(python_code)

    if black:
        try:
            python_code = format_file_contents(python_code, fast=False, mode=FileMode())
        except NothingChanged:
            pass

    # Restore ipython %magic.
    cleaned_code = re.sub("^##%##", "%", python_code, flags=re.M)
    return cleaned_code


def create_file(file_path, contents):
    """Write `contents` to `file_path`."""
    file_path.touch()
    file_path.open("w", encoding="utf-8").write(contents)


def clean_py(py_file_path, autoflake=True, isort=True, black=True):
    """Load, clean and write .py source, write cleaned file back to disk."""
    with open(py_file_path, "r") as file:
        source = file.read()

    clean_lines = clean_python_code(
        "".join(source), isort=isort, black=black, autoflake=autoflake
    )
    create_file(Path(py_file_path), clean_lines)


def clean_ipynb(
    ipynb_file_path, keep_output=False, autoflake=True, isort=True, black=True
):
    """Load, clean and write .ipynb source in-place, back to original file."""
    # Check that conversion can take place cleanly.
    jupytext(("--test-strict", "--to", "py:percent", str(ipynb_file_path)))

    # Carry out the conversion to a Python script.
    jupytext(("--to", "py:percent", str(ipynb_file_path)))

    # Clean the resulting Python file.
    py_file_path = Path(ipynb_file_path).with_suffix(".py")
    clean_py(py_file_path, autoflake=autoflake, isort=isort, black=black)

    # Convert the cleaned Python code back to a Jupyter notebook in-place, taking care
    # to keep the existing output if needed.
    jupytext(
        (
            "--to",
            "ipynb",
            "--output",
            str(ipynb_file_path),
            *(("--update",) if keep_output else ()),
            str(py_file_path),
        )
    )
