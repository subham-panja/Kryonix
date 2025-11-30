from setuptools import setup, find_packages

setup(
    name="kryonix",
    version="0.1.0",
    description="A hyper-advanced Python serialization framework",
    author="Subham Panja",
    packages=find_packages(),
    install_requires=[
        "zstandard",
        "brotli",
    ],
    python_requires=">=3.7",
)
