# -*- coding: utf-8 -*-
"""CLI interface to clean_ipynb."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from multiprocessing import cpu_count
from pathlib import Path
from threading import Lock

import isort.exceptions as isort_exceptions
from wasabi import Printer

from . import __version__
from .clean_ipynb import clean_ipynb, clean_py

msg = Printer()
print_lock = Lock()


def msg_print(cat, text):
    with print_lock:
        getattr(msg, cat)(text)


def main(
    path,
    py=True,
    ipynb=True,
    autoflake=True,
    isort=True,
    black=True,
    keep_output=False,
):
    path = Path(path)
    if not path.is_file():
        raise ValueError("Provide a valid path to a file")

    if path.suffix not in [".py", ".ipynb"]:
        # valid extensions
        raise ValueError("Ensure valid .py or .ipynb path is provided")

    if py and path.suffix == ".py":
        msg_print("info", f"Cleaning file: {path}")
        try:
            clean_py(path, autoflake, isort, black)
        except isort_exceptions.FileSkipComment as exception:
            msg_print("fail", f"Did not clean file: '{path}', due to:\n{exception}.")

    elif ipynb and path.suffix == ".ipynb":
        msg_print("info", f"Cleaning file: {path}")
        clean_ipynb(path, keep_output, autoflake, isort, black)


def main_wrapper():
    parser = argparse.ArgumentParser(
        description=(
            """
Tidy and remove redundant imports (via autoflake), sort imports (via isort), lint and
standardize (via black). Apply equally to entire .py or .ipynb files, or directories
containing such files. Additionally, clear all .ipynb cell outputs and execution
counts (squeeze those diffs!). Cleaning can be carried out using multiple threads with
'--n-jobs N_JOBS', where a positive integer specifies the maximum number of threads to
use. Giving '-1' matches the number of available cores, '-2' results in one less,
etc... By default, only a single thread is used.""".strip()
        )
    )
    parser.add_argument("path", nargs="+", help="File(s) or dir(s) to clean")
    parser.add_argument("-p", "--no-py", help="Ignore .py sources", action="store_true")
    parser.add_argument(
        "-n", "--no-ipynb", help="Ignore .ipynb sources", action="store_true"
    )
    parser.add_argument(
        "-f", "--no-autoflake", help="Do not apply autoflake", action="store_true"
    )
    parser.add_argument(
        "-i", "--no-isort", help="Do not apply isort", action="store_true"
    )
    parser.add_argument(
        "-b", "--no-black", help="Do not apply black", action="store_true"
    )
    parser.add_argument(
        "-j", "--n-jobs", help="Number of threads to use", type=int, default=1
    )
    parser.add_argument(
        "-o",
        "--keep-output",
        help="Do not clear jupyter notebook output",
        action="store_true",
    )
    parser.add_argument(
        "-v",
        "--version",
        help=f"Show the %(prog)s version number",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    args = parser.parse_args()

    if args.no_py and args.no_ipynb:
        raise ValueError(
            "Processing of both Python and Jupyter notebook files disabled."
        )
    if args.no_autoflake and args.no_isort and args.no_black and args.keep_output:
        raise ValueError(
            "All processing disabled. Remove one or more flags to permit processing."
        )

    def path_iter():
        for path in map(Path, args.path):
            if path.is_dir():
                msg_print("info", f"Recursively cleaning directory: {path}")
                if not args.no_py:
                    # Recursively apply to all .py source within dir.
                    for match in path.rglob("*.py"):
                        yield match
                if not args.no_ipynb:
                    # Recursively apply to all .ipynb source within dir.
                    for match in path.rglob("*.ipynb"):
                        yield match
            else:
                yield path

    n_jobs = args.n_jobs if args.n_jobs > 0 else (cpu_count() + 1 + args.n_jobs)

    with ThreadPoolExecutor(max_workers=n_jobs) as executor:
        # `list()` is required to know about Exceptions.
        list(
            executor.map(
                partial(
                    main,
                    py=not args.no_py,
                    ipynb=not args.no_ipynb,
                    autoflake=not args.no_autoflake,
                    isort=not args.no_isort,
                    black=not args.no_black,
                    keep_output=args.keep_output,
                ),
                path_iter(),
            )
        )
