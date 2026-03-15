import streamlit as st

THEME_CSS = """
<style>
  /* Background and surfaces */
  .stApp { background-color: #fdf6ec !important; }
  [data-testid="stSidebar"] { background-color: #f0e6d3 !important; }
  .stExpander { background-color: #fff8f0; border: 1px solid #e8d5bc; border-radius: 8px; }

  /* Typography */
  h1, h2, h3 { font-family: Georgia, 'Playfair Display', serif; color: #2d1b0e; }
  p, li, label { color: #2d1b0e; font-family: system-ui, sans-serif; line-height: 1.6; }
  .subtext { color: #7a5c42; font-size: 0.9em; }

  /* Accent elements */
  .stButton > button { background-color: #c4622a; color: white; border: none; border-radius: 6px; }
  .stButton > button:hover { background-color: #a84e22; }

  /* Pill badges */
  .pill-surprising { background-color: #4a7c4e; color: white; padding: 2px 10px;
                     border-radius: 12px; font-size: 0.8em; font-weight: 600; }
  .pill-unexpected { background-color: #b8860b; color: white; padding: 2px 10px;
                     border-radius: 12px; font-size: 0.8em; font-weight: 600; }
  .pill-classic { background-color: #888; color: white; padding: 2px 10px;
                  border-radius: 12px; font-size: 0.8em; font-weight: 600; }

  /* Molecule tags */
  .molecule-tag { background-color: #e8d5bc; color: #2d1b0e; padding: 2px 8px;
                  border-radius: 4px; font-size: 0.78em; margin: 2px; display: inline-block; }

  /* Borders */
  hr { border-color: #e8d5bc; }
</style>
"""


def inject_theme() -> None:
    """Inject earthy food-forward CSS theme. Call as first action in every page."""
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def pill_html(label: str) -> str:
    """Return HTML for a colored surprise label pill badge."""
    css_class = f"pill-{label.lower()}"
    return f'<span class="{css_class}">{label}</span>'


def molecule_tag_html(name: str) -> str:
    """Return HTML for a molecule inline tag."""
    return f'<span class="molecule-tag">{name}</span>'
