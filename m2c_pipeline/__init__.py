"""
m2c_pipeline — Mermaid-to-Chiikawa Pipeline

Convert Mermaid diagrams in Markdown files into Chiikawa-style illustrations
using Gemini Flash (translation) and Gemini native image generation.
"""

from .config import VertexConfig
from .extractor import MermaidBlock, MermaidExtractor
from .pipeline import M2CPipeline
from .translator import ImagePrompt, MermaidTranslator

__all__ = [
    "VertexConfig",
    "MermaidBlock",
    "MermaidExtractor",
    "M2CPipeline",
    "ImagePrompt",
    "MermaidTranslator",
]
