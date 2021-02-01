# -*- coding: utf-8 -*-

from setuptools import find_packages, setup

with open("README.md") as f:
    long_description = f.read()

with open("requirements.txt", "r") as f:
    required = f.read().splitlines()

setup(
    name="clean_ipynb",
    description="Clean Python code and Jupyter notebooks.",
    url=f"https://github.com/KwatME/clean_ipynb",
    author="Kwat Medetgul-Ernar",
    author_email="kwatme8@gmail.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    entry_points={"console_scripts": ["clean_ipynb=clean_ipynb.cli:main_wrapper"]},
    python_requires=">=3.6",
    setup_requires=["setuptools-scm"],
    use_scm_version=dict(write_to="src/clean_ipynb/_version.py"),
    install_requires=required,
    extras_require={"test": ["pytest>=5.4", "pytest-cov>=2.8"]},
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
