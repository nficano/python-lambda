"""This module contains setup instructions for python-lambda."""
import codecs
import os
import sys
from shutil import rmtree

from setuptools import find_packages
from setuptools import Command
from setuptools import setup

PACKAGE_DATA = {
    "aws_lambda": ["project_templates/*"],
    "": ["*.json"],
}
THIS_DIR = os.path.abspath(os.path.dirname(__file__))
README = os.path.join(THIS_DIR, "README.md")

with codecs.open(README, encoding="utf-8") as fh:
    long_description = "\n" + fh.read()


class UploadCommand(Command):
    """Support setup.py publish."""

    description = "Build and publish the package."
    user_options = []

    @staticmethod
    def status(s):
        """Print in bold."""
        print(f"\033[1m{s}\033[0m")

    def initialize_options(self):
        """Initialize options."""
        pass

    def finalize_options(self):
        """Finialize options."""
        pass

    def run(self):
        """Upload release to Pypi."""
        try:
            self.status("Removing previous builds ...")
            rmtree(os.path.join(THIS_DIR, "dist"))
        except Exception:
            pass
        self.status("Building Source distribution ...")
        os.system(f"{sys.executable} setup.py sdist")
        self.status("Uploading the package to PyPI via Twine ...")
        os.system("twine upload dist/*")
        sys.exit()


setup(
    name="python-lambda",
    version="10.0.4",
    author="Nick Ficano",
    author_email="nficano@gmail.com",
    packages=find_packages(),
    url="https://github.com/nficano/python-lambda",
    license="ISCL",
    package_data=PACKAGE_DATA,
    test_suite="tests",
    tests_require=[],
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: ISC License (ISCL)",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    description="The bare minimum for a Python app running on Amazon Lambda.",
    include_package_data=True,
    long_description_content_type="text/markdown",
    long_description=long_description,
    zip_safe=True,
    cmdclass={"upload": UploadCommand},
    scripts=["scripts/lambda"],
)
