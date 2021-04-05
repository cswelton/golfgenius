import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="golfgenius",
    version="1.0.1",
    author="Craig Welton",
    description="Parse data from golf genius",
    install_requires=[
        'selenium==3.141.0',
        'beautifulsoup4==4.9.0',
        'numpy>=1.19.4'
    ],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cswelton/golfgenius/golfgenius",
    packages=['golfgenius'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    license='MIT',
    include_package_data=True,
    test_suite='nose.collector',
    tests_require=['nose'],
    zip_safe=False)

