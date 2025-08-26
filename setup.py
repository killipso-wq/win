from setuptools import setup, find_packages

setup(
    name="nfl-gpp-simulator",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "streamlit>=1.29.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "nfl_data_py>=0.3.0",
        "pyarrow>=12.0.0",
        "python-slugify>=8.0.0",
        "scipy>=1.11.0",
        "scikit-learn>=1.3.0",
        "watchdog>=3.0.0",
    ],
    python_requires=">=3.10",
)