# Ref:
#     http://docs.python.org/distutils/setupscript.html#meta-data
#     http://pypi.python.org/pypi?%3Aaction=list_classifiers

# Backward compatibility with older Python
# patch distutils if it can't cope with the "classifiers" or
# "download_url" keywords
from setuptools import setup, find_packages

setup(
    name='django-site-multitenancy',
    version='0.1.0',
    author='Chris Malek',
    author_email='cmalek@placodermi.org',
    packages=find_packages(),
    url='https://github.com/cmalek/django-site-multitenancy',
    license='LICENSE.txt',
    description='Enable multitenancy for django projects',
    long_description=open('README.md').read(),
    install_requires=[
        'django-crequest',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Internet :: WWW/HTTP :: Site Management',
    ],
)
