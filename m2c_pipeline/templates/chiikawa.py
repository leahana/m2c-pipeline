"""
Chiikawa (ちいかわ) official manga style template for m2c_pipeline.

Character mapping:
  - Core Actor (trigger/initiator)     -> Chiikawa (吉伊)
  - Logic Processor (narrator/explainer) -> Hachiware (小八)
  - Loop / Exception / High-energy logic -> Usagi (乌萨奇)
"""

from .base import StyleTemplate


# Structured template — injected into Gemini system instruction
_TEMPLATE_SKELETON = """
Chiikawa (ちいかわ) official manga style educational illustration, [ASPECT_RATIO], explaining [TOPIC].

=== TITLE ===
"[MAIN_TITLE]" — floating typography, NOT anchored to any solid band or box; coral-pink (#FF8E9E) bold rounded font with White Outer Glow and Subtle Drop Shadow for legibility on light backgrounds; surrounded by small pastel flowers, twinkling stars, and tiny hearts woven naturally into the scene
[SUBTITLE_IF_NEEDED]

=== SCENE & LAYOUT ===
Layout: [LAYOUT_TYPE] (e.g., problem-solution bridge crossing a gap / circular lifecycle flow / structured comparison table with checks and crosses / "do vs don't" split panel / input-process-output equation / vertical feature list / fishbone cause-effect diagram / narrowing funnel chart / iceberg surface-vs-hidden diagram / winding roadmap journey / layered technology stack, based on the logic of the MAIN CONTENT below)

Background: Soft gradient cream (#FFF8E7) to [THEME_COLOR], minimal [DECORATIVE_ELEMENTS]

=== MAIN CONTENT ===
Use different official Chiikawa Characters such as Chiikawa / Hachiware / Usagi
[CONTENT_SECTION_1]
Character: [CHARACTER_NAME]
- [CHARACTER_ACTION_AND_EXPRESSION]
- [PROPS_OR_ITEMS]
Visual: [KEY_VISUAL_ELEMENT]
Label: "[LABEL_TEXT]" — inside a semi-transparent cloud-like blob (marshmallow-soft aesthetic, pure white at 70–80% opacity, NO hard border, soft edges blending into the background)
[DIALOGUE_OR_ANNOTATION]

[CONTENT_SECTION_2]
[Similar structure as above]

[CONTENT_SECTION_N]
[Continue as needed]

=== KEY CONCEPTS ===
[NUMBER] floating info boxes; each box uses a semi-transparent cloud-like blob background (marshmallow-soft, pure white at 70–80% opacity, no hard border), text in dark charcoal (#2D2D2D), medium-weight sans-serif:
Box 1: "[CONCEPT_1]"
Box 2: "[CONCEPT_2]"
Box N: "[CONCEPT_N]"

=== CHIIKAWA STYLE ===
Official Chiikawa aesthetic: round bodies, large sparkly eyes, pink blush (三), tiny limbs, super deformed proportions, gentle line art

=== TEXT RENDERING ===
Typography rules (CRITICAL — apply to every label, title, and annotation):
- Title: floating typography with White Outer Glow or Subtle Drop Shadow — NO solid background band; title integrates naturally into the illustrated scene with decorative Chiikawa elements around it
- All labels placed inside semi-transparent cloud-like blobs (marshmallow-soft, pure white at 70–80% opacity, no hard borders) — soft edges naturally blend into the illustrated background
- Font: bold (600–700) rounded sans-serif for title; medium-weight (500–600) for labels; NO thin, cursive, or brush-stroke fonts
- Text color: dark charcoal (#2D2D2D) on the light blob background; minimum contrast 4.5:1
- Chinese characters: every stroke and radical must be Fully Formed and Vector-style clarity — no hairline breaks, no missing components, no pixelation
- Smooth anti-aliased edges; absolutely NO cracked, fragmented, or glitchy strokes

=== MOOD ===
[EMOTIONAL_TONE], [EDUCATIONAL_GOAL], cute but informative

Quality: High-quality Chiikawa illustration, clear visual hierarchy, [PURPOSE]
""".strip()

_SYSTEM_INSTRUCTION = """
You are an expert Chiikawa manga artist and educational illustrator.
Your task: analyse the given Mermaid diagram and produce a complete image generation prompt in the structured Chiikawa template format below.

## Label Preservation (HIGHEST PRIORITY)
- All Chinese text from the Mermaid diagram nodes and labels MUST be kept VERBATIM in the prompt. DO NOT translate them to English.
- Use the original Chinese for Labels, Annotations, Dialogue, Key Concepts, and Title.
- You may add English translations in parentheses AFTER the Chinese, e.g. Label: "终止进程 (Terminate)"

## Character Mapping Rules
Use different official Chiikawa characters. Assign each character a distinct role based on the diagram's logic:
- **Chiikawa (吉伊)**: the trigger/initiator — small, round, white marshmallow body, timid but brave, dot eyes, pink blush (三).
- **Hachiware (小八)**: the explainer/decision-maker — black-and-white cat, signature cracked forehead pattern, calm and reliable, holds clipboard or pointer.
- **Usagi (乌萨奇)**: high-energy/action/conclusion — tall beige rabbit, long ears, wide round eyes, energetic jumping pose.
A character MAY appear in multiple sections if the diagram logic requires it (e.g. Chiikawa at start AND at a panic branch), but avoid unnecessary repetition.

## Aspect Ratio Selection
- Simple linear flow (≤5 nodes)  → recommend "1:1"
- Wide horizontal flowchart / roadmap → recommend "16:9"
- Tall vertical or stacked layout → recommend "9:16"
State your recommendation on the FIRST line of your response as: ASPECT_RATIO: <value>

## Output Format
After the ASPECT_RATIO line, output the filled-in Chiikawa template EXACTLY as shown below.
Do NOT add any commentary, markdown fences, or extra text outside the template.

ASPECT_RATIO: <1:1 | 9:16 | 16:9>

""" + _TEMPLATE_SKELETON + """

## Filling Instructions
- [TOPIC]: a short description of what the diagram explains
- [MAIN_TITLE]: use the original Chinese from the diagram context, or create a concise Chinese title
- [SUBTITLE_IF_NEEDED]: a Chinese subtitle, or leave blank
- [LAYOUT_TYPE]: pick the best layout descriptor for this diagram's shape
- [THEME_COLOR]: a complementary pastel hex colour
- Fill each [CONTENT_SECTION] with: Character, Action, Props, Visual, Label (in Chinese), and Dialogue/Annotation (in Chinese)
- [KEY_CONCEPTS]: summarize key takeaways from the diagram in Chinese
- Keep label text short (≤ 6 Chinese characters) for crisp rendering; if longer, abbreviate and explain in KEY CONCEPTS
"""


class ChiikawaTemplate(StyleTemplate):
    """Chiikawa manga style illustration template."""

    @property
    def name(self) -> str:
        return "chiikawa"

    @property
    def character_mapping(self) -> dict[str, str]:
        return {
            "core_actor": "Chiikawa (吉伊)",
            "logic_processor": "Hachiware (小八)",
            "high_energy": "Usagi (乌萨奇)",
        }

    def get_system_instruction(self) -> str:
        return _SYSTEM_INSTRUCTION

    def build_prompt(self, topic: str, mermaid_source: str, aspect_ratio: str) -> str:
        """Fallback prompt when Gemini output cannot be parsed."""
        return (
            f"Chiikawa (ちいかわ) official manga style educational illustration, "
            f"aspect ratio {aspect_ratio}, explaining {topic}. "
            f"Soft gradient background from cream (#FFF8E7) to light blue (#E8F4FD), "
            f"minimal twinkling stars and tiny hearts as decoration. "
            f"Title in floating typography — coral-pink (#FF8E9E) bold rounded font with "
            f"White Outer Glow and Subtle Drop Shadow, surrounded by small pastel flowers; "
            f"NO solid header band. "
            f"Chiikawa (white marshmallow blob, black dot eyes, pink triple-line blush) "
            f"stands at the start looking curious. "
            f"Hachiware (black-and-white cat with signature cracked pattern on forehead) "
            f"holds a pointer in the middle, explaining. "
            f"Usagi (tall beige rabbit with long ears and wide round eyes) "
            f"jumps excitedly at the end. "
            f"Nodes as soft rounded bubbles, hand-drawn style arrows. "
            f"Nagano (ナガノ) art style: ultra-minimalist thin black outlines, no shading, "
            f"flat pastel fills, 1:1 head-to-body ratio, warm and healing. "
            f"All text labels inside semi-transparent cloud-like blobs (marshmallow-soft, "
            f"pure white at 70–80% opacity, no hard border), medium-weight sans-serif, "
            f"dark charcoal on blob background; Chinese characters Fully Formed with "
            f"Vector-style clarity, no cracked or missing strokes."
        )
