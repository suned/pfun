import os
import sys

sys.path.insert(0, os.path.abspath('../..'))

project = 'pfun'
copyright = '2019, Sune Debel'
author = 'Sune Debel'
version = ''
release = '0.5.1'
source_suffix = ['.rst', '.md']
master_doc = 'index'
extensions = ['recommonmark', 'sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx_autodoc_typehints', 'sphinx_rtd_theme']
html_theme = 'sphinx_rtd_theme'
intersphinx_mapping = {'aiohttp': ('https://docs.aiohttp.org/en/stable/', None)}
