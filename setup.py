from setuptools import setup, find_packages
from setuptools.command.install import install
import os
import sys
import pkgutil


def get_root_path(import_name):
    """Returns the path to a package or cwd if that cannot be found.  This
    returns the path of a package or the folder that contains a module.

    Not to be confused with the package path returned by :func:`find_package`.
    """
    # Module already imported and has a file attribute.  Use that first.
    mod = sys.modules.get(import_name)
    if mod is not None and hasattr(mod, '__file__'):
        return os.path.dirname(os.path.abspath(mod.__file__))

    # Next attempt: check the loader.
    loader = pkgutil.get_loader(import_name)

    # Loader does not exist or we're referring to an unloaded main module
    # or a main module without path (interactive sessions), go with the
    # current working directory.
    if loader is None or import_name == '__main__':
        return os.getcwd()

    # For .egg, zipimporter does not have get_filename until Python 2.7.
    # Some other loaders might exhibit the same behavior.
    if hasattr(loader, 'get_filename'):
        filepath = loader.get_filename(import_name)
    else:
        # Fall back to imports.
        __import__(import_name)
        mod = sys.modules[import_name]
        filepath = getattr(mod, '__file__', None)

        # If we don't have a filepath it might be because we are a
        # namespace package.  In this case we pick the root path from the
        # first module that is contained in our package.
        if filepath is None:
            raise RuntimeError('No root path can be found for the provided '
                               'module "%s".  This can happen because the '
                               'module came from an import hook that does '
                               'not provide file name information or because '
                               'it\'s a namespace package.  In this case '
                               'the root path needs to be explicitly '
                               'provided.' % import_name)

    # filepath is import_name.py for a module, or __init__.py for a package.
    return os.path.dirname(os.path.abspath(filepath))


class post_install(install):
    def run(self):
        install.run(self)
        cwd = os.getcwd()
        sys.path.remove(cwd)
        pkgpath = get_root_path('frasco_sharejs')
        sys.path.append(cwd)
        os.chdir(os.path.join(pkgpath, 'sharejs'))
        os.system('npm install')
        os.chdir(cwd)


setup(
    name='frasco-sharejs',
    version='0.1.1',
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