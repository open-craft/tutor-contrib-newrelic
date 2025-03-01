import io
import os

from setuptools import find_packages, setup

HERE = os.path.abspath(os.path.dirname(__file__))


def load_readme():
    with io.open(os.path.join(HERE, "README.rst"), "rt", encoding="utf8") as f:
        return f.read()


def load_about():
    about = {}
    with io.open(
        os.path.join(HERE, "tutornewrelic", "__about__.py"),
        "rt",
        encoding="utf-8",
    ) as f:
        exec(f.read(), about)  # pylint: disable=exec-used
    return about


ABOUT = load_about()


setup(
    name="tutor-contrib-newrelic",
    version=ABOUT["__version__"],
    url="https://github.com/open-craft/tutor-contrib-newrelic",
    project_urls={
        "Code": "https://github.com/open-craft/tutor-contrib-newrelic",
        "Issue tracker": "https://github.com/open-craft/tutor-contrib-newrelic/issues",
    },
    license="AGPLv3",
    author="Gabor Boros",
    author_email="gabor@opencraft.com",
    description="NewRelic plugin for Tutor",
    long_description=load_readme(),
    long_description_content_type="text/x-rst",
    packages=find_packages(exclude=["tests*"]),
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=[
        "tutor>=17,<20",
        "requests",
        "pydantic",
    ],
    extras_require={
        "dev": [
            "black",
            "mypy",
            "pylint",
            "tutor[dev]>=17,<20",
            "types-requests",
        ]
    },
    entry_points={
        "tutor.plugin.v1": [
            "newrelic = tutornewrelic.plugin"
        ]
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
