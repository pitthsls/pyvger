"""Installer."""
from os.path import dirname, join

from setuptools import find_packages, setup

_version = {}
with open(join(dirname(__file__), "pyvger", "version.py")) as fp:
    exec(fp.read(), _version)


setup(
    python_requires=">=3.6",
    name="pyvger",
    description="Interact with Ex Libris Voyager ILS",
    version=_version["__version__"],
    packages=find_packages(),
    author="Geoffrey Spear",
    author_email="geoffspear@gmail.com",
    keywords="library voyager batchcat ILS cataloging MARC",
    install_requires=[
        "pymarc>=2.8.4",
        "cx_Oracle>=5.1.2",
        "sqlAlchemy",
        "six",
        "arrow",
    ],
    extras_require={"BatchCat": ["pywin32"]},
    tests_require=["mock", "pytest", "pytest-mock"],
)
