from setuptools import setup, find_packages
from setuptools.command.install import install
import os
import subprocess


class post_install(install):
    def run(self):
        install.run(self)
        cwd = os.getcwd()
        os.chdir(os.path.join(self.install_lib, 'frasco_sharejs', 'sharejs'))
        try:
            subprocess.check_call(['npm', 'install'])
        except:
            self.warn(("Failed to install nodejs dependencies."
                "Make sure you have nodejs installed on the machine and try again"))
        os.chdir(cwd)


setup(
    name='frasco-sharejs',
    version='0.1.2',
    url='http://github.com/frascoweb/frasco-sharejs',
    license='MIT',
    author='Maxime Bouroumeau-Fuseau',
    author_email='maxime.bouroumeau@gmail.com',
    description="Sharejs integration into Frasco",
    packages=find_packages(),
    package_data={
        'frasco_sharejs': [
            'static/*.js',
            'sharejs/*.json',
            'sharejs/*.js']
    },
    zip_safe=False,
    platforms='any',
    install_requires=[
        'frasco',
        'requests'
    ],
    cmdclass={'install': post_install}
)