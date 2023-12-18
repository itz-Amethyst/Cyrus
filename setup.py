"""Installation script for Perseus."""
from pathlib import Path
from setuptools import setup , find_packages

DESCRIPTION = "Perseus_Kit: Elevate FastAPI with Intelligent Caching by Redis"
APP_ROOT = Path(__file__).resolve().parent
README = (APP_ROOT / "README.md").read_text(encoding = 'utf-8').strip()
AUTHOR = "itz-Amethyst"
AUTHOR_EMAIL = "pransermi@gmail.com"
PROJECT_URLS = {
    "Bug Tracker": "https://github.com/itz-Amethyst/Perseus/issues",
    "Source Code": "https://github.com/itz-Amethyst/Perseus",
    "Documentation": "https://pypi.org/project/Perseus",
}
KEYWORDS = 'Redis, Redis Caching, Redis Connection, Redis client instance'


CLASSIFIERS = [
    "Framework :: FastAPI",
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Natural Language :: English",
    "Natural Language :: Persian",
    "Operating System :: Microsoft :: Windows",
    "Operating System :: MacOS :: MacOS X",
    "Operating System :: POSIX :: Linux",
    "Operating System :: Unix",
    "Programming Language :: Python :: 3 :: Only",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",

]
INSTALL_REQUIRES = [
    "fastapi",
    "pydantic",
    "python-dateutil",
    "redis",
]

# Execute version.py and get __version__
version_globals = {}
exec(open(str(APP_ROOT / "src/Perseus/version.py")).read(), version_globals)
__version__ = version_globals['__version__']


setup(
    name="Perseus_Kit",
    description=DESCRIPTION,
    long_description=README,
    long_description_content_type="text/markdown",
    version=__version__,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    keywords = KEYWORDS,
    maintainer=AUTHOR,
    maintainer_email=AUTHOR_EMAIL,
    license="MIT",
    url=PROJECT_URLS["Source Code"],
    project_urls=PROJECT_URLS,
    packages = find_packages(where = "src") ,
    package_dir = {"": "src"} ,
    include_package_data=True,
    python_requires=">=3.7",
    classifiers=CLASSIFIERS,
    install_requires=INSTALL_REQUIRES,
    # zip_safe=True
)