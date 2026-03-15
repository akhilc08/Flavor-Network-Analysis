import streamlit as st

THEME_CSS = """
<style>
  /* ── HIDE STREAMLIT CHROME ── */
  [data-testid="stAppHeader"]               { display: none !important; }
  [data-testid="stAppToolbar"]              { display: none !important; }
  [data-testid="stAppDeployButton"]         { display: none !important; }
  [data-testid="stMainMenu"]                { display: none !important; }
  [data-testid="stMainMenuButton"]          { display: none !important; }
  #MainMenu                                 { display: none !important; }
  footer                                    { display: none !important; }
  [data-testid="stSidebar"]                 { display: none !important; }
  [data-testid="stSidebarCollapsedControl"] { display: none !important; }
  [data-testid="stExpandSidebarButton"]     { display: none !important; }

  /* ── BACKGROUNDS ── */
  .stApp,
  [data-testid="stAppViewContainer"] { background-color: #fdf6ec !important; }

  /* ── MAIN CONTENT ── */
  [data-testid="stMain"]               { padding-top: 0 !important; }
  [data-testid="stMainBlockContainer"] {
    padding-top: 0 !important;
    padding-left: 48px !important;
    padding-right: 48px !important;
    padding-bottom: 48px !important;
    max-width: 1280px !important;
  }

  /* ── TOP NAV CONTAINER ── */
  /* Target the first stHorizontalBlock inside the first stColumn set = our nav row */
  div[data-testid="stNavContainer"] {
    position: sticky !important;
    top: 0 !important;
    z-index: 9999 !important;
    background: #fdf6ec !important;
    border-bottom: 1px solid #e8d5bc !important;
    margin-left: -48px !important;
    margin-right: -48px !important;
    padding: 0 48px !important;
  }

  /* ── PAGE LINKS — style st.page_link as nav items ── */
  [data-testid="stPageLink-NavLink"] {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    height: 44px !important;
    display: flex !important;
    align-items: center !important;
  }
  [data-testid="stPageLink-NavLink"] p {
    font-family: system-ui, sans-serif !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: #7a5c42 !important;
    margin: 0 !important;
    line-height: 44px !important;
    border-bottom: 2px solid transparent !important;
    padding-bottom: 2px !important;
  }
  [data-testid="stPageLink-NavLink"]:hover p { color: #c4622a !important; }
  [data-testid="stPageLink-NavLink"][aria-current="page"] p,
  [data-testid="stPageLink-NavLink"].active p {
    color: #c4622a !important;
    border-bottom-color: #c4622a !important;
  }
  /* Logo link — larger Georgia serif */
  .fn-logo-col [data-testid="stPageLink-NavLink"] p {
    font-family: Georgia, serif !important;
    font-size: 16px !important;
    font-weight: 400 !important;
    letter-spacing: -0.02em !important;
    text-transform: none !important;
    color: #2d1b0e !important;
  }
  .fn-logo-col [data-testid="stPageLink-NavLink"]:hover p { color: #c4622a !important; }

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

  /* ── LINKS ── */
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


def inject_theme() -> None:
    """Inject theme CSS and render top nav using st.page_link (Streamlit's native router)."""
    st.markdown(THEME_CSS, unsafe_allow_html=True)

    # Nav bar using native st.page_link — Streamlit's own router handles navigation
    with st.container():
        logo_col, _, c1, c2, c3, c4 = st.columns([3, 4, 1, 1, 1, 1])
        with logo_col:
            st.markdown('<div class="fn-logo-col">', unsafe_allow_html=True)
            st.page_link("app.py", label="FlavorNet")
            st.markdown('</div>', unsafe_allow_html=True)
        with c1:
            st.page_link("pages/1_Search.py", label="Search")
        with c2:
            st.page_link("pages/2_Rate.py", label="Rate")
        with c3:
            st.page_link("pages/3_Graph.py", label="Graph")
        with c4:
            st.page_link("pages/4_Recipe.py", label="Recipe")

    st.markdown(
        '<div style="height:1px;background:#e8d5bc;margin:0 0 32px"></div>',
        unsafe_allow_html=True,
    )


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
