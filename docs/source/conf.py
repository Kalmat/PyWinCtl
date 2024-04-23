# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'PyWinCtl'
copyright = '2024, Kalmat'
author = 'Kalmat'
release = '0.4'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ["myst_parser"]

myst_enable_extensions = ["colon_fence"]

source_suffix = {
    '.rst': 'restructuredtext',
    '.txt': 'markdown',
    '.md': 'markdown',
}
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
myst_heading_anchors = 7

# -- Copy the modules documentation ------------------------------------------
# https://stackoverflow.com/questions/66495200/is-it-possible-to-include-external-rst-files-in-my-documentation
from urllib.request import urlretrieve

urlretrieve (
    "https://raw.githubusercontent.com/kalmat/pywinctl/master/README.md",
    "README.md"
)
urlretrieve (
    "https://raw.githubusercontent.com/kalmat/pywinctl/master/docstrings.md",
    "docstrings.md"
)
