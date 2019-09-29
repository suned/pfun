import os
import sys

sys.path.insert(0, os.path.abspath('../..'))

project = 'pfun'
copyright = '2019, Sune Debel'
author = 'Sune Debel'
version = ''
release = '0.1.0'
source_suffix = ['.rst', '.md']
master_doc = 'index'
pygments_style = 'sphinx'
html_theme = 'sphinx_rtd_theme'
extensions = [
    'recommonmark',
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx'
]
