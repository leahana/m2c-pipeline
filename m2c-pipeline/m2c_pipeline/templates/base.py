"""
Abstract base class for m2c_pipeline style templates.

To add a new style (e.g. Monster Hunter, SOMA):
  1. Create templates/your_style.py and implement StyleTemplate
  2. Register it in templates/__init__.py: TEMPLATE_REGISTRY["your_style"] = YourClass
  3. Use via CLI: --template your_style
"""

from abc import ABC, abstractmethod


class StyleTemplate(ABC):
    """Interface for illustration style templates."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique template identifier (matches registry key)."""
        ...

    @property
    @abstractmethod
    def character_mapping(self) -> dict[str, str]:
        """Maps logical roles to style-specific character names.

        Required keys:
          - "core_actor":      The trigger/initiator node
          - "logic_processor": Narrating / explaining nodes
          - "high_energy":     Loop, exception, or dramatic logic nodes
        """
        ...

    @abstractmethod
    def get_system_instruction(self) -> str:
        """Full system prompt for Gemini.

        Must instruct the model to:
        - Analyse the mermaid diagram
        - Map nodes to characters using character_mapping
        - Output a complete image-generation prompt in the style's template format
        - Recommend an aspect ratio
        """
        ...

    @abstractmethod
    def build_prompt(
        self,
        topic: str,
        mermaid_source: str,
        aspect_ratio: str,
    ) -> str:
        """Assemble a minimal fallback image-generation prompt without Gemini.

        Used when Gemini output cannot be parsed and a best-effort
        prompt is needed to keep the pipeline running.
        """
        ...
