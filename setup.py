"""Bootstrapper for docker's ENTRYPOINT executable."""
import os
from setuptools import setup


ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
REPO = "https://github.com/"
repo = os.getenv("GITHUB_REPOSITORY", None)  # in case this is published from a fork
REPO += "cpp-linter/cpp-linter-action" if repo is None else repo


setup(
    name="cpp_linter",
    # use_scm_version=True,
    # setup_requires=["setuptools_scm"],
    version="1.4.2",
    description=__doc__,
    long_description=(
        "A python package that powers the github action named cpp-linter-action. "
        + f"See `the github repository README <{REPO}#readme>`_ for full details."
    ),
    author="Brendan Doherty",
    author_email="2bndy5@gmail.com",
    install_requires=["requests", "pyyaml"],  # pyyaml is installed with clang-tidy
    license="MIT",
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    keywords="clang clang-tidy clang-format",
    packages=["cpp_linter"],
    entry_points={"console_scripts": ["cpp-linter=cpp_linter.run:main"]},
    # Specifiy your homepage URL for your project here
    url=REPO,
    download_url=f"{REPO}/releases",
)
