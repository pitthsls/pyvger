from setuptools import setup, find_packages

setup(
    name='pyvger',
    description='Interact with Ex Libris Voyager ILS',
    version='0.1a1',
    packages=find_packages(),
    author='Geoffrey Spear',
    author_email='geoffspear@gmail.com',
    keywords='library voyager batchcat ILS cataloging MARC',
    test_suite='pyvger.test',
    install_requires=['pymarc>=2.8.4',
                      'cx_Oracle>=5.1.2',
                      'sqlAlchemy',
    ],
    extras_require={
        'BatchCat': ["pywin32"],
    }
)
