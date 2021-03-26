from pathlib import Path

from setuptools import setup, find_packages

setup(name='spectrochempy_gui',
      use_scm_version=True,
      author="Christian Fernandez",
      author_email="christian.fernandez (at) ensicaen.fr",
      url='http:/www.spectrochempy.fr',
      description='GUI for SpectroChemPy',
      long_description=Path('README.md').read_text(),
      long_description_content_type="text/markdown",
      platforms=['Windows', 'Mac OS X', 'Linux'],  # packages discovery
      zip_safe=False,
      python_requires=">=3.6.9",
      setup_requires=['setuptools_scm'], packages=find_packages(), )
