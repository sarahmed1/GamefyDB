from pathlib import Path
import streamlit.components.v1 as components

_LANG_CODES = {"EN": "en-US", "FR": "fr-FR", "AR": "ar-TN"}

_voice_input = components.declare_component(
    "voice_input",
    path=str(Path(__file__).parent / "voice_html"),
)


def voice_input(language: str = "EN") -> str | None:
    return _voice_input(lang=_LANG_CODES.get(language, "en-US"), default=None)
