"""
BOS Documents - Renderer Public API
=====================================
"""

from core.documents.renderer.html_renderer import render_html
from core.documents.renderer.pdf_renderer import render_pdf

__all__ = [
    "render_html",
    "render_pdf",
]
