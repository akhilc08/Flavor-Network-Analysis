import streamlit as st

THEME_CSS = """
<style>
  /* ── HIDE STREAMLIT CHROME (Streamlit 1.55 correct selectors) ── */
  [data-testid="stAppHeader"]          { display: none !important; }
  [data-testid="stAppToolbar"]         { display: none !important; }
  [data-testid="stToolbar"]            { display: none !important; }
  [data-testid="stAppDeployButton"]    { display: none !important; }
  [data-testid="stMainMenu"]           { display: none !important; }
  [data-testid="stMainMenuButton"]     { display: none !important; }
  #MainMenu                            { display: none !important; }
  footer                               { display: none !important; }

  /* ── BACKGROUNDS ── */
  .stApp,
  [data-testid="stAppViewContainer"]   { background-color: #fdf6ec !important; }

  /* ── MAIN CONTENT AREA — remove top gap left by hidden header ── */
  [data-testid="stMain"]               { padding-top: 0 !important; }
  [data-testid="stMainBlockContainer"] {
    padding-top: 24px !important;
    padding-left: 48px !important;
    padding-right: 48px !important;
    padding-bottom: 48px !important;
    max-width: 1280px !important;
  }

  /* ── SIDEBAR ── */
  [data-testid="stSidebar"]            { background-color: #f0e6d3 !important; border-right: 1px solid #e8d5bc !important; }
  [data-testid="stSidebarHeader"]      { background-color: #f0e6d3 !important; border-bottom: 1px solid #e8d5bc !important; padding: 20px 24px 16px !important; }
  [data-testid="stSidebarContent"]     { background-color: #f0e6d3 !important; }
  [data-testid="stSidebarUserContent"] { padding: 16px 0 !important; }

  /* Sidebar nav links */
  [data-testid="stSidebarNavItems"]    { padding: 0 !important; }
  [data-testid="stSidebarNavLink"]     {
    padding: 10px 24px !important;
    border-radius: 0 !important;
    font-family: system-ui, sans-serif !important;
    font-size: 14px !important;
    font-weight: 400 !important;
    color: #2d1b0e !important;
    background: transparent !important;
    border-left: 3px solid transparent !important;
    transition: background 0.15s, color 0.15s !important;
  }
  [data-testid="stSidebarNavLink"]:hover {
    background: rgba(196,98,42,0.07) !important;
    color: #c4622a !important;
  }
  [data-testid="stSidebarNavLink"][aria-current="page"] {
    background: rgba(196,98,42,0.1) !important;
    color: #c4622a !important;
    font-weight: 600 !important;
    border-left: 3px solid #c4622a !important;
  }
  /* Sidebar nav link icons and text */
  [data-testid="stSidebarNavLinkContainer"] span { color: inherit !important; }
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] span,
  [data-testid="stSidebar"] div { color: #2d1b0e !important; }

  /* ── TYPOGRAPHY ── */
  h1, h2, h3, h4 {
    font-family: Georgia, serif !important;
    color: #2d1b0e !important;
    font-weight: 400 !important;
  }
  h1 { font-size: 32px !important; line-height: 1.2 !important; }
  h2 { font-size: 24px !important; line-height: 1.25 !important; }
  h3 { font-size: 18px !important; line-height: 1.3 !important; }
  p, li, label {
    font-family: system-ui, sans-serif !important;
    color: #2d1b0e !important;
    line-height: 1.6 !important;
  }

  /* ── SELECTION ── */
  ::selection { background: rgba(196,98,42,0.2); }

  /* ── STRIP ALL BLUE ── */
  a { color: #c4622a !important; }
  a:hover { color: #a84e22 !important; }
  [data-baseweb="tab-highlight"]              { background-color: #c4622a !important; }
  [data-testid="stBaseButton-primary"]        { background-color: #c4622a !important; border-color: #c4622a !important; }
  [data-testid="stBaseButton-primary"]:hover  { background-color: #a84e22 !important; }

  /* ── TEXT INPUT ── */
  .stTextInput input, [data-testid="stTextInput"] input {
    font-family: Georgia, serif !important;
    background-color: #fff8f0 !important;
    border: 1.5px solid #e8d5bc !important;
    border-radius: 4px !important;
    color: #2d1b0e !important;
    font-size: 16px !important;
    padding: 10px 14px !important;
  }
  .stTextInput input:focus, [data-testid="stTextInput"] input:focus {
    border-color: #c4622a !important;
    box-shadow: 0 0 0 1px rgba(196,98,42,0.2) !important;
    outline: none !important;
  }
  .stTextInput label, [data-testid="stTextInput"] label {
    font-family: system-ui, sans-serif !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: #7a5c42 !important;
  }

  /* ── SELECT / MULTISELECT ── */
  [data-baseweb="select"] > div {
    background-color: #fff8f0 !important;
    border-color: #e8d5bc !important;
    border-radius: 4px !important;
  }
  [data-baseweb="select"] input { color: #2d1b0e !important; font-family: Georgia, serif !important; }
  [data-baseweb="menu"]          { background-color: #fff8f0 !important; border: 1px solid #e8d5bc !important; }
  [data-baseweb="option"]        { background-color: #fff8f0 !important; color: #2d1b0e !important; }
  [data-baseweb="option"]:hover  { background-color: #f0e6d3 !important; }
  [data-baseweb="tag"]           { background-color: rgba(196,98,42,0.1) !important; color: #c4622a !important; }

  /* ── BUTTONS ── */
  .stButton > button,
  button[kind="primary"],
  button[data-testid="stBaseButton-primary"],
  button[data-testid="stBaseButton-secondary"] {
    background-color: #c4622a !important;
    color: #fff !important;
    border: none !important;
    border-radius: 4px !important;
    font-family: system-ui, sans-serif !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    padding: 10px 24px !important;
    cursor: pointer !important;
  }
  .stButton > button:hover,
  button[kind="primary"]:hover { background-color: #a84e22 !important; }

  /* ── SLIDERS ── */
  [role="slider"]                                              { background-color: #c4622a !important; border-color: #c4622a !important; }
  [data-testid="stSlider"] [data-baseweb="slider"] div[class] { background-color: #c4622a !important; }
  .stSlider label {
    font-family: system-ui, sans-serif !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: #7a5c42 !important;
  }

  /* ── METRICS ── */
  [data-testid="stMetricValue"] { font-family: Georgia, serif !important; color: #2d1b0e !important; font-size: 28px !important; }
  [data-testid="stMetricLabel"] { font-family: system-ui !important; font-size: 10px !important; letter-spacing: 0.1em !important; text-transform: uppercase !important; color: #7a5c42 !important; }
  [data-testid="stMetricDelta"] { font-family: Georgia, serif !important; }

  /* ── ALERTS ── */
  [data-testid="stAlert"] { background-color: #fff8f0 !important; border-radius: 4px !important; border: 1px solid #e8d5bc !important; border-left: 3px solid #c4622a !important; }
  [data-testid="stAlert"] p { color: #2d1b0e !important; }

  /* ── SPINNER ── */
  [data-testid="stSpinner"] > div { border-top-color: #c4622a !important; }

  /* ── TABLES ── */
  table { border-collapse: collapse !important; }
  th { background-color: #f0e6d3 !important; color: #2d1b0e !important; font-family: system-ui !important; font-size: 10px !important; font-weight: 600 !important; letter-spacing: 0.1em !important; text-transform: uppercase !important; border: 1px solid #e8d5bc !important; padding: 8px 16px !important; }
  td { background-color: #fff8f0 !important; color: #2d1b0e !important; border: 1px solid #e8d5bc !important; padding: 8px 16px !important; font-family: Georgia, serif !important; }
  tr:hover td { background-color: #f5ead6 !important; }

  /* ── DIVIDERS ── */
  hr { border-color: #e8d5bc !important; margin: 24px 0 !important; }
</style>
"""


_SIDEBAR_HEADER = """
<div style="padding:4px 0 20px">
  <div style="font-family:Georgia,serif;font-size:17px;font-weight:400;color:#2d1b0e;letter-spacing:-0.01em;line-height:1.2">
    Flavor Pairing<br><span style="color:#c4622a">Network</span>
  </div>
  <div style="font-family:system-ui;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:#7a5c42;margin-top:4px">
    Molecular gastronomy
  </div>
</div>
<div style="height:1px;background:#e8d5bc;margin:0 -16px 20px"></div>
<div style="font-family:system-ui;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:#7a5c42;font-weight:600;margin-bottom:4px">
  Navigation
</div>
"""


def inject_theme() -> None:
    """Inject Editorial CSS theme + sidebar header. Call as first action in every page."""
    st.markdown(THEME_CSS, unsafe_allow_html=True)
    st.sidebar.markdown(_SIDEBAR_HEADER, unsafe_allow_html=True)


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
