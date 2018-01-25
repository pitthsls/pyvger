from setuptools import setup, find_packages

setup(
    name='pyvger',
    description='Interact with Ex Libris Voyager ILS',
    version='0.8.0',
    packages=find_packages(),
    author='Geoffrey Spear',
    author_email='geoffspear@gmail.com',
    keywords='library voyager batchcat ILS cataloging MARC',
    install_requires=['pymarc>=2.8.4',
                      'cx_Oracle>=5.1.2',
                      'sqlAlchemy',
                      'six',
                      'arrow'
    ],
    extras_require={
        'BatchCat': ["pywin32"],
    },
    tests_require=[
        'mock',
        'pytest',
    ],

)
