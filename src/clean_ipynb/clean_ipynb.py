# -*- coding: utf-8 -*-
import re
from functools import partial
from json import dump, load
from multiprocessing import cpu_count
from multiprocessing.dummy import Pool
from pathlib import Path
from subprocess import run

from autoflake import fix_code
from black import FileMode, NothingChanged, format_file_contents
from isort import code

__all__ = (
    "clean_ipynb",
    "clean_ipynb_cell",
    "clean_py",
    "clean_python_code",
    "clear_ipynb_output",
)


def clean_python_code(python_code, isort=True, black=True, autoflake=True):
    """Temporarily comment out IPython %magic to avoid Black errors."""
    python_code = re.sub("^%", "##%##", python_code, flags=re.M)

    # run source code string through autoflake, isort, and black
    if autoflake:
        # programmatic autoflake
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

    # restore ipython %magic
    cleaned_code = re.sub("^##%##", "%", python_code, flags=re.M)
    return cleaned_code


def clear_ipynb_output(ipynb_file_path):
    """Clear cell outputs, reset cell execution counts of Jupyter notebook."""
    run(
        (
            "jupyter",
            "nbconvert",
            "--ClearOutputPreprocessor.enabled=True",
            "--inplace",
            ipynb_file_path,
        ),
        check=True,
    )


def clean_ipynb_cell(cell_dict, autoflake=True, isort=True, black=True):
    """Clean a single cell within a Jupyter notebook."""
    if cell_dict["cell_type"] == "code":
        clean_lines = clean_python_code(
            "".join(cell_dict["source"]), isort=isort, black=black, autoflake=autoflake
        ).split("\n")

        # The above cleaning may produce a trailing newline which will then get
        # transformed to an empty string element in the line list.
        if clean_lines[-1] == "":
            clean_lines = clean_lines[:-1]

        if len(clean_lines) == 1 and clean_lines[0] == "":
            clean_lines = []
        else:
            # All but the last lines have a trailing newline character.
            clean_lines[:-1] = [clean_line + "\n" for clean_line in clean_lines[:-1]]
        cell_dict["source"] = clean_lines
        return cell_dict
    else:
        return cell_dict


def clean_ipynb(
    ipynb_file_path,
    clear_output=True,
    autoflake=True,
    isort=True,
    black=True,
    n_jobs=1,
):
    """Load, clean and write .ipynb source in-place, back to original file.

    Raises:
        ValueError: If `n_jobs` is 0.

    """
    if n_jobs == 0:
        raise ValueError("'n_jobs' cannot be 0.")

    if clear_output:
        clear_ipynb_output(ipynb_file_path)

    with open(ipynb_file_path) as ipynb_file:
        ipynb_dict = load(ipynb_file)

    clean_cell_with_options = partial(
        clean_ipynb_cell, isort=isort, black=black, autoflake=autoflake
    )
    # Multithread the map operation.
    n_jobs = n_jobs if n_jobs > 0 else (cpu_count() + 1 + n_jobs)
    processed_cells = Pool(n_jobs).map(clean_cell_with_options, ipynb_dict["cells"])
    ipynb_dict["cells"] = processed_cells

    with open(ipynb_file_path, "w") as ipynb_file:
        dump(ipynb_dict, ipynb_file, indent=1)
        ipynb_file.write("\n")


def create_file(file_path, contents):
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
