# Configuration file for the Sphinx documentation builder.

project = "TestPioneer"
copyright = "2024, JE-Chen"  # pylint: disable=redefined-builtin  # Sphinx-required name
author = "JE-Chen"
release = "0.1.33"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

language = "en"
