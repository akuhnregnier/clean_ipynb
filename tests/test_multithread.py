# -*- coding: utf-8 -*-
import shutil
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from subprocess import run
from tempfile import NamedTemporaryFile, TemporaryDirectory
from timeit import timeit

import pytest

from clean_ipynb import clean_ipynb, clean_py


def single_expected_comp(filetype, keep_output, raw, known_good):
    """Test the cleaning of a single Python script notebook."""
    fixture_dir = Path(__file__).resolve().parent / "fixtures"
    raw_file = fixture_dir / raw

    # Use a temporary file to contain the cleaned notebook.
    with NamedTemporaryFile(suffix=raw_file.suffix) as temp_cleaned_file:
        temp_clean_filename = temp_cleaned_file.name
        # Copy the original 'dirty' notebook for later in-place cleaning.
        shutil.copy(raw_file, temp_clean_filename)
        # Clean the notebook.
        if raw_file.suffix == ".ipynb":
            clean_ipynb(temp_clean_filename, keep_output=keep_output)
        elif raw_file.suffix == ".py":
            clean_py(temp_clean_filename)
        else:
            raise ValueError(f"Unsupported suffix '{raw_file.suffix}'.")
        # Read the contents of the cleaned notebook.
        with open(temp_clean_filename) as f:
            cleaned = f.read()

    # Compare the known good notebook to the above.
    with open(fixture_dir / known_good) as f:
        target_clean = f.read()

    assert target_clean == cleaned


def multi_expected_comp(filetype, keep_output, raw, known_good, threads):
    """Test the multithreaded cleaning of Python scripts or notebooks."""
    factor = threads * 2
    with ThreadPoolExecutor(max_workers=threads) as executor:
        # `list()` is required to know about Exceptions.
        list(
            executor.map(
                single_expected_comp,
                [filetype] * factor,
                [keep_output] * factor,
                [raw] * factor,
                [known_good] * factor,
            )
        )


@pytest.mark.parametrize(
    "filetype,keep_output,raw,known_good",
    [
        ("ipynb", False, "raw_python_notebook.ipynb", "clean_python_notebook.ipynb"),
        (
            "ipynb",
            True,
            "raw_python_notebook.ipynb",
            "clean_python_notebook_with_output.ipynb",
        ),
    ],
)
def test_module_multithread(filetype, keep_output, raw, known_good):
    """Performance should not increase when the CLI is not being used.

    Note that this test includes to overhead of checking the resulting files.

    """
    partial_comp = partial(multi_expected_comp, **locals())

    timeit_globals = {**globals(), **locals()}
    # Get baseline and multithread time.
    comp_threads = 2
    times = [
        timeit(f"partial_comp(threads={threads})", number=3, globals=timeit_globals)
        for threads in [1, comp_threads]
    ]

    assert times[1] / comp_threads > times[0], "Multithreaded code should be slower."


@pytest.mark.parametrize(
    "filetype,keep_output,raw,known_good",
    [
        ("ipynb", False, "raw_python_notebook.ipynb", "clean_python_notebook.ipynb"),
        (
            "ipynb",
            True,
            "raw_python_notebook.ipynb",
            "clean_python_notebook_with_output.ipynb",
        ),
    ],
)
def test_cli_multithread(filetype, keep_output, raw, known_good):
    """There should be a performance increase for Jupyter notebooks.

    Note that this test includes to overhead of checking the resulting files.

    """
    fixture_dir = Path(__file__).resolve().parent / "fixtures"
    raw_file = fixture_dir / raw

    # Get baseline and multithread time.
    comp_threads = 4

    def cli_comp_func(threads):
        factor = 2 * threads
        with TemporaryDirectory() as temp_dir:
            # Create `factor` copies of the raw file in the temporary directory.
            processed_names = []
            for i in range(factor):
                processed_name = Path(temp_dir) / f"{i}_{raw_file.name}"
                shutil.copy(raw_file, processed_name)
                processed_names.append(processed_name)
            # Process these using the CLI.
            assert not run(
                (
                    "clean_ipynb",
                    *(("--keep-output",) if keep_output else ()),
                    "--n-jobs",
                    str(threads),
                    str(temp_dir),
                )
            ).returncode

            # Check that all the resulting files are identical.
            def content_iter():
                for name in processed_names:
                    with open(Path(temp_dir) / name) as f:
                        yield f.read()

            assert len(set(content_iter())) == 1, "All files should match."

            # Check that the resulting files match the known good output.
            with open(fixture_dir / known_good) as f:
                target_clean = f.read()

            with open(Path(temp_dir) / processed_names[0]) as f:
                cleaned = f.read()

            assert target_clean == cleaned

    timeit_globals = {**globals(), **locals()}
    times = [
        timeit(
            f"cli_comp_func(threads={threads})",
            number=3,
            globals=timeit_globals,
        )
        for threads in [1, comp_threads]
    ]

    assert (
        2 * times[1] / comp_threads < times[0]
    ), "Multithreaded code should be at least 2x faster."
