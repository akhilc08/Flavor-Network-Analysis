"""
FlavorNet — Streamlit Demo
Entry point. Run with: streamlit run app/app.py
Pages auto-discovered from app/pages/ directory.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from utils.theme import inject_theme

st.set_page_config(
    page_title="FlavorNet",
    page_icon="🍓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_theme()

LANDING_CSS = """
<style>
  /* ── LANDING PAGE STYLES ── */
  /* ── HERO ── */
  .hero {
    position: relative;
    padding: 80px 64px 72px;
    border-bottom: 1px solid #e8d5bc;
    overflow: hidden;
  }

  /* Decorative network dots */
  .hero-bg {
    position: absolute;
    inset: 0;
    pointer-events: none;
    overflow: hidden;
  }
  .hero-bg svg {
    position: absolute;
    right: 0;
    top: 0;
    width: 55%;
    height: 100%;
    opacity: 0.18;
  }

  .hero-eyebrow {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #c4622a;
    margin-bottom: 20px;
  }

  .hero-title {
    font-family: Georgia, serif;
    font-size: clamp(52px, 7vw, 88px);
    font-weight: 400;
    line-height: 1.0;
    color: #2d1b0e;
    letter-spacing: -0.03em;
    margin-bottom: 24px;
  }

  .hero-title em {
    font-style: italic;
    color: #c4622a;
  }

  .hero-sub {
    font-size: 16px;
    color: #7a5c42;
    line-height: 1.7;
    max-width: 520px;
    margin-bottom: 44px;
  }

  .hero-cta {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    background: #2d1b0e;
    color: #fdf6ec !important;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    text-decoration: none;
    padding: 14px 28px;
    border-radius: 3px;
    transition: background 0.15s, transform 0.15s;
  }
  .hero-cta:hover {
    background: #c4622a;
    transform: translateY(-1px);
  }
  .hero-cta-arrow {
    font-size: 14px;
    letter-spacing: 0;
    transition: transform 0.15s;
  }
  .hero-cta:hover .hero-cta-arrow { transform: translateX(3px); }

  /* ── STATS BAR ── */
  .stats {
    display: flex;
    gap: 0;
    border-bottom: 1px solid #e8d5bc;
  }
  .stat {
    flex: 1;
    padding: 28px 40px;
    border-right: 1px solid #e8d5bc;
  }
  .stat:last-child { border-right: none; }
  .stat-value {
    font-family: Georgia, serif;
    font-size: 36px;
    font-weight: 400;
    color: #2d1b0e;
    line-height: 1;
    margin-bottom: 6px;
  }
  .stat-label {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #7a5c42;
  }

  /* ── FEATURES ── */
  .features {
    padding: 56px 64px 64px;
  }
  .features-header {
    font-family: Georgia, serif;
    font-size: 11px;
    font-weight: 400;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #7a5c42;
    margin-bottom: 32px;
  }
  .feature-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1px;
    background: #e8d5bc;
    border: 1px solid #e8d5bc;
    border-radius: 4px;
    overflow: hidden;
  }
  .feature-card {
    background: #fff8f0;
    padding: 36px 36px 32px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    text-decoration: none;
    color: inherit;
    transition: background 0.15s;
    cursor: pointer;
  }
  .feature-card:hover { background: #fdf6ec; }
  .feature-card:hover .feature-arrow { transform: translateX(4px); }

  .feature-num {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #c4622a;
  }
  .feature-title {
    font-family: Georgia, serif;
    font-size: 22px;
    font-weight: 400;
    color: #2d1b0e;
    line-height: 1.2;
  }
  .feature-desc {
    font-size: 13px;
    color: #7a5c42;
    line-height: 1.65;
    flex: 1;
  }
  .feature-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-top: 16px;
    border-top: 1px solid #e8d5bc;
    margin-top: 4px;
  }
  .feature-tag {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #c4622a;
    background: rgba(196,98,42,0.08);
    border: 1px solid rgba(196,98,42,0.2);
    padding: 3px 9px;
    border-radius: 2px;
  }
  .feature-arrow {
    font-size: 18px;
    color: #c4622a;
    transition: transform 0.15s;
  }

  /* ── FOOTER ── */
  .footer {
    padding: 24px 64px;
    border-top: 1px solid #e8d5bc;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .footer-brand {
    font-family: Georgia, serif;
    font-size: 14px;
    color: #7a5c42;
  }
  .footer-meta {
    font-size: 11px;
    color: #b8a090;
    letter-spacing: 0.04em;
  }
</style>
"""

LANDING_BODY = """
<!-- ── HERO ── -->
<div class="hero">
  <div class="hero-bg">
    <svg viewBox="0 0 600 400" xmlns="http://www.w3.org/2000/svg">
      <!-- Network graph decoration -->
      <g stroke="#c4622a" stroke-width="1" fill="none">
        <line x1="300" y1="200" x2="480" y2="100"/>
        <line x1="300" y1="200" x2="520" y2="220"/>
        <line x1="300" y1="200" x2="450" y2="320"/>
        <line x1="300" y1="200" x2="180" y2="80"/>
        <line x1="300" y1="200" x2="150" y2="280"/>
        <line x1="300" y1="200" x2="420" y2="180"/>
        <line x1="300" y1="200" x2="370" y2="310"/>
        <line x1="480" y1="100" x2="520" y2="220"/>
        <line x1="480" y1="100" x2="420" y2="180"/>
        <line x1="450" y1="320" x2="520" y2="220"/>
        <line x1="450" y1="320" x2="370" y2="310"/>
        <line x1="180" y1="80"  x2="420" y2="180"/>
        <line x1="150" y1="280" x2="370" y2="310"/>
        <line x1="100" y1="160" x2="180" y2="80"/>
        <line x1="100" y1="160" x2="150" y2="280"/>
        <line x1="560" y1="340" x2="520" y2="220"/>
        <line x1="560" y1="340" x2="450" y2="320"/>
      </g>
      <g fill="#c4622a">
        <circle cx="300" cy="200" r="7"/>
        <circle cx="480" cy="100" r="5"/>
        <circle cx="520" cy="220" r="4"/>
        <circle cx="450" cy="320" r="5"/>
        <circle cx="180" cy="80"  r="4"/>
        <circle cx="150" cy="280" r="4"/>
        <circle cx="420" cy="180" r="3.5"/>
        <circle cx="370" cy="310" r="3.5"/>
        <circle cx="100" cy="160" r="3"/>
        <circle cx="560" cy="340" r="3"/>
      </g>
    </svg>
  </div>

  <div class="hero-eyebrow">Graph Neural Network &middot; Molecular Gastronomy</div>
  <h1 class="hero-title">Discover hidden<br><em>flavor pairings</em></h1>
  <p class="hero-sub">
    A graph neural network trained on flavor chemistry surfaces ingredient
    combinations that are scientifically compatible but culinarily underexplored.
    Explore the molecular bridges between unexpected ingredients.
  </p>
  <a href="/1_Search" target="_self" class="hero-cta">
    Start Exploring
    <span class="hero-cta-arrow">&#8594;</span>
  </a>
</div>

<!-- ── STATS BAR ── -->
<div class="stats">
  <div class="stat">
    <div class="stat-value">935</div>
    <div class="stat-label">Ingredients</div>
  </div>
  <div class="stat">
    <div class="stat-value">436k</div>
    <div class="stat-label">Scored pairs</div>
  </div>
  <div class="stat">
    <div class="stat-value">128</div>
    <div class="stat-label">Embedding dims</div>
  </div>
  <div class="stat">
    <div class="stat-value">GAT</div>
    <div class="stat-label">Model architecture</div>
  </div>
</div>

<!-- ── FEATURES ── -->
<div class="features">
  <div class="features-header">What you can do</div>
  <div class="feature-grid">

    <a href="/1_Search" target="_self" class="feature-card">
      <div class="feature-num">01</div>
      <div class="feature-title">Ingredient Search</div>
      <div class="feature-desc">
        Type any ingredient and instantly surface its top molecular pairings,
        ranked by a surprise score that balances pairing quality against
        culinary familiarity. Each result shows shared flavor compounds and
        a Classic / Unexpected / Surprising label.
      </div>
      <div class="feature-footer">
        <span class="feature-tag">Search</span>
        <span class="feature-arrow">&#8594;</span>
      </div>
    </a>

    <a href="/2_Rate" target="_self" class="feature-card">
      <div class="feature-num">02</div>
      <div class="feature-title">Rate & Improve</div>
      <div class="feature-desc">
        The model is uncertain about some pairs — those whose predicted
        co-occurrence score hovers near 0.5. Rate them to trigger active
        learning fine-tuning and watch the validation AUC rise in real time.
      </div>
      <div class="feature-footer">
        <span class="feature-tag">Active Learning</span>
        <span class="feature-arrow">&#8594;</span>
      </div>
    </a>

    <a href="/3_Graph" target="_self" class="feature-card">
      <div class="feature-num">03</div>
      <div class="feature-title">Flavor Graph</div>
      <div class="feature-desc">
        Navigate the ingredient network visually. Select any ingredient to
        re-center the graph on it. Edge width reflects surprise score —
        thicker means more unexpected. Terracotta edges are novel pairings;
        blue edges are expected ones.
      </div>
      <div class="feature-footer">
        <span class="feature-tag">Network Explorer</span>
        <span class="feature-arrow">&#8594;</span>
      </div>
    </a>

    <a href="/4_Recipe" target="_self" class="feature-card">
      <div class="feature-num">04</div>
      <div class="feature-title">Recipe Generation</div>
      <div class="feature-desc">
        Pick 2–3 surprising ingredients and generate a recipe with a
        molecular rationale written by Claude. The model explains the
        chemical bridges between ingredients and proposes a dish that
        exploits those shared aromatic compounds.
      </div>
      <div class="feature-footer">
        <span class="feature-tag">AI Generation</span>
        <span class="feature-arrow">&#8594;</span>
      </div>
    </a>

  </div>
</div>

<!-- ── FOOTER ── -->
<div class="footer">
  <div class="footer-brand">FlavorNet</div>
  <div class="footer-meta">Graph Neural Network &middot; Flavor Chemistry &middot; Active Learning</div>
</div>
"""

st.markdown(LANDING_CSS, unsafe_allow_html=True)
st.markdown(LANDING_BODY, unsafe_allow_html=True)
