import streamlit as st

THEME_CSS = """
<style>
  /* Hide Streamlit chrome */
  header[data-testid="stHeader"] { background-color: #fdf6ec !important; }
  [data-testid="stToolbar"] { display: none; }
  #MainMenu { visibility: hidden; }
  footer { visibility: hidden; }

  /* Background and surfaces */
  .stApp { background-color: #fdf6ec !important; }
  [data-testid="stSidebar"] { background-color: #f0e6d3 !important; }
  [data-testid="stSidebar"] * { color: #2d1b0e !important; }
  .stExpander { background-color: #fff8f0 !important; border: 1px solid #e8d5bc !important; border-radius: 8px !important; }
  [data-testid="stExpander"] { background-color: #fff8f0 !important; border: 1px solid #e8d5bc !important; border-radius: 8px !important; }

  /* Typography */
  h1, h2, h3, .stTitle { font-family: Georgia, 'Playfair Display', serif !important; color: #2d1b0e !important; }
  p, li, label, .stMarkdown { color: #2d1b0e !important; font-family: system-ui, sans-serif !important; line-height: 1.6 !important; }
  .subtext { color: #7a5c42 !important; font-size: 0.9em !important; }

  /* Table styling — remove blue highlight from markdown tables */
  table { border-collapse: collapse; width: auto; }
  th { background-color: #f0e6d3 !important; color: #2d1b0e !important; font-family: Georgia, serif !important; border: 1px solid #e8d5bc !important; padding: 8px 16px !important; }
  td { background-color: #fff8f0 !important; color: #2d1b0e !important; border: 1px solid #e8d5bc !important; padding: 8px 16px !important; }
  tr:hover td { background-color: #f5ead6 !important; }

  /* Accent elements */
  .stButton > button { background-color: #c4622a !important; color: white !important; border: none !important; border-radius: 6px !important; font-weight: 600 !important; }
  .stButton > button:hover { background-color: #a84e22 !important; }

  /* Inputs */
  .stTextInput input, .stSelectbox select { background-color: #fff8f0 !important; border: 1px solid #e8d5bc !important; color: #2d1b0e !important; border-radius: 6px !important; }

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

  /* Borders and dividers */
  hr { border-color: #e8d5bc !important; }
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
