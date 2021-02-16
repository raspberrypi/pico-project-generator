import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup (
    name = "pico-project-generator",
    version = "0.1",
    description = "Console and GUI C project generator for the Raspberry Pi Pico",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/raspberrypi/pico-project-generator",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Topic :: Software Development",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Software Development :: Embedded Systems",
    ],
    python_requires = '>=3.6',
    package_data = {
        'pico_project': ['logo_alpha.gif', 'pico_configs.tsv']
    },
    packages = ["pico_project"],
    entry_points = {
        'console_scripts': [
            'pico_project=pico_project.pico_project:main',
        ],
    }
)

