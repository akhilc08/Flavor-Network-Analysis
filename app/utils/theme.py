import streamlit as st

THEME_CSS = """
<style>
  /* ── Hide all Streamlit chrome ── */
  header[data-testid="stHeader"] { display: none !important; }
  [data-testid="stToolbar"] { display: none !important; }
  #MainMenu { display: none !important; }
  footer { display: none !important; }
  [data-testid="stDeployButton"] { display: none !important; }
  button[kind="header"] { display: none !important; }
  .stAppDeployButton { display: none !important; }
  [data-testid="manage-app-button"] { display: none !important; }

  /* ── App background ── */
  .stApp { background-color: #fdf6ec !important; }
  .main .block-container {
    padding-top: 16px !important;
    padding-bottom: 40px !important;
    max-width: 1200px !important;
  }

  /* ── Sidebar ── */
  [data-testid="stSidebar"] {
    background-color: #f0e6d3 !important;
    border-right: 1px solid #e8d5bc !important;
  }
  [data-testid="stSidebar"] * { color: #2d1b0e !important; }
  [data-testid="stSidebarNav"] a {
    font-family: system-ui, sans-serif !important;
    font-size: 13px !important;
    letter-spacing: 0.02em !important;
    color: #2d1b0e !important;
  }
  [data-testid="stSidebarNav"] a:hover { color: #c4622a !important; }

  /* ── Typography ── */
  h1, h2, h3, h4 {
    font-family: Georgia, serif !important;
    color: #2d1b0e !important;
    font-weight: 400 !important;
  }
  h1 { font-size: 32px !important; line-height: 1.2 !important; }
  h2 { font-size: 24px !important; line-height: 1.25 !important; }
  h3 { font-size: 18px !important; line-height: 1.3 !important; }
  p, li, label, .stMarkdown p {
    font-family: system-ui, sans-serif !important;
    color: #2d1b0e !important;
    line-height: 1.6 !important;
  }

  /* ── Selection highlight ── */
  ::selection { background: rgba(196,98,42,0.2) !important; }

  /* ── Remove ALL blue from Streamlit defaults ── */
  a { color: #c4622a !important; }
  a:hover { color: #a84e22 !important; }
  .stSelectbox [data-baseweb="select"] *,
  [data-baseweb="tab-highlight"] { background-color: #c4622a !important; }
  [data-testid="stTickBarMin"], [data-testid="stTickBarMax"] { color: #7a5c42 !important; }
  .stSlider [data-baseweb="slider"] [data-testid="stThumbValue"] { color: #2d1b0e !important; }
  .stSlider [role="slider"] { background-color: #c4622a !important; border-color: #c4622a !important; }
  .stSlider [data-baseweb="slider"] div[style*="background"] { background-color: #c4622a !important; }

  /* ── Inputs ── */
  .stTextInput input {
    font-family: Georgia, serif !important;
    background-color: #fff8f0 !important;
    border: 1px solid #e8d5bc !important;
    border-radius: 4px !important;
    color: #2d1b0e !important;
    font-size: 15px !important;
  }
  .stTextInput input:focus {
    border-color: #c4622a !important;
    box-shadow: 0 0 0 1px rgba(196,98,42,0.25) !important;
  }
  .stTextInput label {
    font-family: system-ui, sans-serif !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: #7a5c42 !important;
  }

  /* ── Selectbox / multiselect ── */
  [data-baseweb="select"] {
    background-color: #fff8f0 !important;
    border-color: #e8d5bc !important;
  }
  [data-baseweb="select"] input { color: #2d1b0e !important; }
  [data-baseweb="select"] [data-testid="stMarkdownContainer"] { color: #2d1b0e !important; }

  /* ── Buttons ── */
  .stButton > button {
    background-color: #c4622a !important;
    color: #fff !important;
    border: none !important;
    border-radius: 4px !important;
    font-family: system-ui, sans-serif !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    padding: 8px 20px !important;
  }
  .stButton > button:hover { background-color: #a84e22 !important; }
  .stButton > button:focus { box-shadow: 0 0 0 2px rgba(196,98,42,0.3) !important; }

  /* ── Expander (used in rate page fallback) ── */
  .stExpander,
  [data-testid="stExpander"] {
    background-color: #fff8f0 !important;
    border: 1px solid #e8d5bc !important;
    border-radius: 4px !important;
  }

  /* ── Table overrides ── */
  table { border-collapse: collapse !important; width: auto !important; }
  th {
    background-color: #f0e6d3 !important;
    color: #2d1b0e !important;
    font-family: system-ui, sans-serif !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    border: 1px solid #e8d5bc !important;
    padding: 8px 16px !important;
  }
  td {
    background-color: #fff8f0 !important;
    color: #2d1b0e !important;
    border: 1px solid #e8d5bc !important;
    padding: 8px 16px !important;
    font-family: Georgia, serif !important;
  }
  tr:hover td { background-color: #f5ead6 !important; }

  /* ── HR / dividers ── */
  hr { border-color: #e8d5bc !important; margin: 24px 0 !important; }

  /* ── Metrics ── */
  [data-testid="stMetricValue"] {
    font-family: Georgia, serif !important;
    color: #2d1b0e !important;
  }
  [data-testid="stMetricLabel"] {
    font-family: system-ui, sans-serif !important;
    font-size: 10px !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: #7a5c42 !important;
  }

  /* ── Info / warning / success boxes ── */
  [data-testid="stAlert"] {
    border-radius: 4px !important;
    border-left: 3px solid #c4622a !important;
  }

  /* ── Spinner ── */
  .stSpinner > div { border-top-color: #c4622a !important; }
</style>
"""


def inject_theme() -> None:
    """Inject Editorial CSS theme. Call as first action in every page."""
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def pill_html(label: str) -> str:
    """Return HTML for an outline-style surprise label pill badge."""
    label_lower = label.lower()
    pill_styles = {
        'surprising': (
            'background:rgba(74,124,78,0.12);color:#4a7c4e;'
            'border:1px solid rgba(74,124,78,0.25)'
        ),
        'unexpected': (
            'background:rgba(184,134,11,0.12);color:#b8860b;'
            'border:1px solid rgba(184,134,11,0.25)'
        ),
        'classic': (
            'background:rgba(196,98,42,0.1);color:#c4622a;'
            'border:1px solid rgba(196,98,42,0.25)'
        ),
    }
    style = pill_styles.get(label_lower, pill_styles['classic'])
    base = (
        'font-family:system-ui;font-size:11px;font-weight:600;'
        'letter-spacing:0.08em;text-transform:uppercase;'
        'padding:4px 10px;border-radius:2px;display:inline-block;'
    )
    return f'<span style="{base}{style}">{label}</span>'


def molecule_tag_html(name: str) -> str:
    """Return HTML for a molecule inline tag."""
    style = (
        'font-family:system-ui;font-size:11px;font-style:italic;'
        'color:#7a5c42;background:#fdf6ec;border:1px solid #e8d5bc;'
        'border-radius:2px;padding:3px 8px;margin:2px;display:inline-block'
    )
    return f'<span style="{style}">{name}</span>'
