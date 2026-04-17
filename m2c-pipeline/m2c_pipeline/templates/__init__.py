"""
Template registry for m2c_pipeline style templates.

To add a new style:
  1. Create templates/<style_name>.py implementing StyleTemplate
  2. Import it here and add to TEMPLATE_REGISTRY
"""

from .base import StyleTemplate
from .chiikawa import ChiikawaTemplate

# Registry: template name -> class
TEMPLATE_REGISTRY: dict[str, type[StyleTemplate]] = {
    "chiikawa": ChiikawaTemplate,
    # "monster_hunter": MonsterHunterTemplate,  # future
    # "soma": SomaTemplate,                      # future
}


def get_template(name: str) -> StyleTemplate:
    """Return an instantiated template by name.

    Raises:
        KeyError: if the template name is not registered.
    """
    if name not in TEMPLATE_REGISTRY:
        available = ", ".join(sorted(TEMPLATE_REGISTRY.keys()))
        raise KeyError(
            f"Unknown template '{name}'. "
            f"Available templates: {available}"
        )
    return TEMPLATE_REGISTRY[name]()
