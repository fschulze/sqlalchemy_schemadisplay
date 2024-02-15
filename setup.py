from setuptools import setup

import os

version = '1.4'

long_description = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()

setup(
    name='sqlalchemy_schemadisplay',
    version=version,
    description="Turn SQLAlchemy DB Model into a graph",
    author="Florian Schulze",
    author_email="florian.schulze@gmx.net",
    license="MIT License",
    long_description=long_description[long_description.find('\n\n'):],
    url='https://github.com/fschulze/sqlalchemy_schemadisplay',
    py_modules=['sqlalchemy_schemadisplay'],
    zip_safe=True,
    install_requires=[
        'setuptools',
        'sqlalchemy < 2',
        'pydot',
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Database :: Front-Ends",
        "Operating System :: OS Independent"],
)
