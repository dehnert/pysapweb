from distutils.core import setup

with open("README.rst") as f:
    README = f.read()

setup(
    name = "pysapweb",
    packages = ["pysapweb"],
    version = "0.9.1",
    install_requires = ["selenium"],

    author = "btidor",
    author_email = "pysapweb@mit.edu",
    url = "https://github.com/btidor/pysapweb",
    description = "A Python interface to MIT's SAPweb (now Atlas) accounting system.",
    long_description = README,
    license = "LICENSE.txt",

    keywords = ["sapweb", "atlas", "accounting"],
    classifiers = [
        "Programming Language :: Python",
        "Development Status :: 4 - Beta",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business :: Financial :: Accounting",
    ],
)
