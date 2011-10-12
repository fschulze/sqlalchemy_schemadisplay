from setuptools import setup

import os

version = '1.1'

long_description = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()

setup(
    name='sqlalchemy_schemadisplay',
    version=version,
    description="Turn SQLAlchemy DB Model into a graph",
    long_description=long_description[long_description.find('\n\n'):],
    url='https://github.com/fschulze/sqlalchemy_schemadisplay',
    py_modules=['sqlalchemy_schemadisplay'],
    zip_safe=True,
    install_requires=[
        'setuptools',
        'pydot',
    ],
)
