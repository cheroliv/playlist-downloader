from setuptools import setup, find_packages

setup(
    name="playlist-downloader",
    version="0.1.0",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    install_requires=[
        "typer[all]",
        "pymonad>=2.4.0",
        "yt-dlp",
        "google-api-python-client",
        "google-auth-oauthlib",
        "PyYAML",
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-mock",
            "ruff",
            "setuptools",
            "wheel",
            "twine",
        ]
    },
    entry_points={
        "console_scripts": [
            "playlist-downloader = cli:app",
        ],
    },
    author="Your Name",  # TODO: Replace with actual author name
    author_email="your.email@example.com",  # TODO: Replace with actual author email
    description="A CLI tool to manage YouTube playlists.",
    long_description=open("README.adoc").read(),
    long_description_content_type="text/asciidoc",
    url="https://github.com/your-username/playlist-downloader",  # TODO: Replace with actual GitHub URL
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Internet :: WWW/HTTP",
    ],
    python_requires=">=3.8",
)
