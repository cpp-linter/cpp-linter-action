"""Bootstrapper for docker's ENTRYPOINT executable."""
import os
import subprocess
from setuptools import setup


ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
REPO = "https://github.com/"
repo = os.getenv("GITHUB_REPOSITORY", None)
REPO += "" if repo is None else repo
if repo is None:
    REPO += "2bndy5/cpp-linter"

version = "v1.2.1"
# with open("clang-tidy_output.json", "w", encoding="utf-8") as std_out:
#     subprocess.run(["git", "describe", "--tags", "--abbrev=0"], stdout=std_out)
# with open("clang-tidy_output.json", "r", encoding="utf-8") as std_out:
#     version = std_out.readline().strip("\n")
#     # print("Version: ", version)

setup(
    name="python_action",
    # use_scm_version=True,
    # setup_requires=["setuptools_scm"],
    version=version.lower().lstrip("v"),
    description=__doc__,
    long_description=".. warning:: this is not meant for PyPi (yet)",
    author="Brendan Doherty",
    author_email="2bndy5@gmail.com",
    install_requires=["requests", "pyyaml", "unidiff"],
    license="MIT",
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Development Status :: 1 - Production/Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    keywords="clang clang-tidy clang-format",
    packages = ["python_action"],

    entry_points = {"console_scripts": ["run-action=python_action.run:main"]},
    # Specifiy your homepage URL for your project here
    url=REPO,
    download_url=f"{REPO}/releases",
)
