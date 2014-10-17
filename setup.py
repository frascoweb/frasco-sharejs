from setuptools import setup, find_packages


def desc():
    with open("README.md") as f:
        return f.read()

def reqs():
    with open('requirements.txt') as f:
        return f.read().splitlines()

setup(
    name='frasco-sharejs',
    version='0.1',
    url='http://github.com/frascoweb/frasco-sharejs',
    license='MIT',
    author='Maxime Bouroumeau-Fuseau',
    author_email='maxime.bouroumeau@gmail.com',
    description="Sharejs integration into Frasco",
    long_description=desc(),
    py_modules=["frasco_push"],
    platforms='any',
    install_requires=reqs() + [
        'frasco'
    ]
)