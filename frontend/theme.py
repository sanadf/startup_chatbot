"""Visual theme for the Startup Chatbot interface.

One dark, AI-native surface: Inter everywhere, a single accent, and a quiet
chrome so the conversation is the only thing that carries weight.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

FONT_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Inter:wght@300;400;500;600;700&display=swap"
)

STYLES = f"""
<style>
@import url('{FONT_URL}');

:root {{
  --sc-bg: #0B0B0F;
  --sc-surface: #121218;
  --sc-surface-2: #17171F;
  --sc-surface-3: #1D1D26;
  --sc-border: rgba(255, 255, 255, .08);
  --sc-border-strong: rgba(255, 255, 255, .14);
  --sc-text: #ECECF1;
  --sc-text-muted: #9A9AA8;
  --sc-primary: #7C3AED;
  --sc-primary-soft: rgba(124, 58, 237, .16);
  --sc-radius-sm: 10px;
  --sc-radius: 14px;
  --sc-radius-lg: 20px;
  --sc-ease: cubic-bezier(.2, .8, .2, 1);
}}

html, body, .stApp, button, input, textarea, select {{
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}}

/* Streamlit draws icons as ligatures, so they must keep their own font —
   inheriting Inter would print the raw glyph name next to the label. */
[data-testid="stIconMaterial"],
span.material-symbols-rounded,
[class*="material-symbols"] {{
  font-family: 'Material Symbols Rounded' !important;
}}

.stApp {{ background: var(--sc-bg); }}

h1, h2, h3, h4, h5 {{
  letter-spacing: -.021em;
  font-weight: 600;
  color: var(--sc-text);
}}

/* ---------- App shell ---------- */

.block-container {{
  max-width: 940px;
  padding-top: 2.25rem;
  padding-bottom: 9rem;
}}

header[data-testid="stHeader"] {{ background: transparent; }}

[data-testid="stStatusWidget"],
[data-testid="stAppDeployButton"],
[data-testid="stMainMenu"] {{ display: none !important; }}

[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapseButton"] {{
  display: flex !important;
  visibility: visible !important;
  opacity: 1 !important;
}}

/* ---------- Sidebar ---------- */

[data-testid="stSidebar"] {{
  background: var(--sc-surface);
  border-right: 1px solid var(--sc-border);
}}

[data-testid="stSidebar"] .block-container,
[data-testid="stSidebarUserContent"] {{ padding-top: 1.25rem; }}

.sc-brand {{
  display: flex;
  align-items: center;
  gap: .625rem;
  padding: .25rem .25rem 1.125rem;
}}

.sc-brand__mark {{
  width: 28px;
  height: 28px;
  border-radius: 9px;
  background: linear-gradient(140deg, #8B5CF6, #4F46E5 55%, #0891B2);
  flex: 0 0 auto;
}}

.sc-brand__name {{
  font-size: 1.0625rem;
  font-weight: 600;
  letter-spacing: -.02em;
  color: var(--sc-text);
}}

.sc-group-label {{
  font-size: .6875rem;
  font-weight: 600;
  letter-spacing: .07em;
  text-transform: uppercase;
  color: var(--sc-text-muted);
  padding: .25rem .25rem .5rem;
}}

/* Conversation rows are real buttons, toned down to read as a quiet list.
   The active thread is the one with a filled surface. */
[data-testid="stSidebar"] .stButton > button[kind="tertiary"],
[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
  background: transparent;
  border-color: transparent;
  color: var(--sc-text-muted);
  font-weight: 400;
  min-height: 38px;
  padding: .45rem .6rem;
}}

[data-testid="stSidebar"] .stButton > button[kind="tertiary"]:hover {{
  background: var(--sc-surface-2);
  color: var(--sc-text);
}}

[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
  background: var(--sc-surface-3);
  color: var(--sc-text);
}}

/* Streamlit centres button content; sidebar rows read better flush left. */
[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] .stButton > button > div {{
  justify-content: flex-start;
  width: 100%;
}}

[data-testid="stSidebar"] .stButton > button p {{
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}}

/* ---------- Hero ---------- */

.sc-hero {{
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 3.5rem 1rem 1.25rem;
}}

/* Layered highlights give the sphere an iridescent, pearl-like surface
   rather than a flat purple disc. */
.sc-orb {{
  width: 104px;
  height: 104px;
  border-radius: 50%;
  background:
    radial-gradient(circle at 26% 22%, rgba(255, 255, 255, .95) 0%, rgba(255, 255, 255, 0) 32%),
    radial-gradient(circle at 72% 30%, rgba(125, 211, 252, .75) 0%, rgba(125, 211, 252, 0) 42%),
    radial-gradient(circle at 70% 76%, rgba(244, 114, 182, .60) 0%, rgba(244, 114, 182, 0) 46%),
    radial-gradient(circle at 30% 80%, rgba(167, 243, 208, .45) 0%, rgba(167, 243, 208, 0) 44%),
    radial-gradient(circle at 50% 42%, #CBBFF2 0%, #8B7FD4 48%, #4C3F8F 78%, #241E42 100%);
  box-shadow:
    inset 0 -10px 22px -10px rgba(10, 8, 30, .75),
    0 0 0 1px rgba(255, 255, 255, .12),
    0 26px 64px -20px rgba(124, 58, 237, .55);
  animation: sc-float 7s var(--sc-ease) infinite;
}}

@keyframes sc-float {{
  0%, 100% {{ transform: translateY(0); }}
  50%      {{ transform: translateY(-9px); }}
}}

.sc-hero .sc-hero__greeting {{
  margin-top: 1.75rem;
  max-width: 28rem;
  font-size: clamp(1.4rem, 1.05rem + 1.3vw, 1.875rem);
  font-weight: 400;
  line-height: 1.3;
  letter-spacing: -.028em;
  color: var(--sc-text);
}}

.sc-hero .sc-hero__sub {{
  margin-top: .625rem;
  max-width: 34rem;
  font-size: .9375rem;
  line-height: 1.6;
  color: var(--sc-text-muted);
}}

/* ---------- Chat messages ---------- */

[data-testid="stChatMessage"] {{
  background: transparent;
  padding: 1rem 0;
  margin-bottom: .25rem;
  border-radius: 0;
}}

[data-testid="stChatMessageAvatarUser"],
[data-testid="stChatMessageAvatarAssistant"] {{ display: none !important; }}

[data-testid="stChatMessage"] > div:first-child:empty {{ display: none; }}

[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {{
  background: var(--sc-surface-2);
  border: 1px solid var(--sc-border);
  border-radius: var(--sc-radius-lg);
  padding: .9rem 1.15rem;
  margin: .5rem 0 1rem auto;
  max-width: 78%;
}}

/* ---------- Composer ---------- */

[data-testid="stBottomBlockContainer"] {{
  background: linear-gradient(to top, var(--sc-bg) 62%, rgba(11, 11, 15, 0));
  padding-bottom: 1.5rem;
}}

[data-testid="stChatInput"] {{
  background: var(--sc-surface-2);
  border: 1px solid var(--sc-border-strong);
  border-radius: var(--sc-radius-lg);
  box-shadow: 0 18px 40px -24px rgba(0, 0, 0, .9);
  transition: border-color 180ms var(--sc-ease), box-shadow 180ms var(--sc-ease);
}}

[data-testid="stChatInput"]:focus-within {{
  border-color: rgba(124, 58, 237, .7);
  box-shadow: 0 0 0 3px var(--sc-primary-soft);
}}

[data-testid="stChatInput"] textarea {{
  font-size: .9375rem;
  line-height: 1.55;
  color: var(--sc-text);
}}

[data-testid="stChatInput"] textarea::placeholder {{ color: var(--sc-text-muted); }}

/* ---------- Buttons ---------- */

.stButton > button,
.stDownloadButton > button {{
  background: var(--sc-surface-2);
  border: 1px solid var(--sc-border);
  border-radius: var(--sc-radius);
  color: var(--sc-text);
  font-size: .8125rem;
  font-weight: 450;
  line-height: 1.5;
  min-height: 44px;
  padding: .7rem .95rem;
  text-align: left;
  cursor: pointer;
  transition: background 170ms var(--sc-ease), border-color 170ms var(--sc-ease),
              color 170ms var(--sc-ease);
}}

/* Let prompt cards wrap onto several lines instead of truncating. */
.stButton > button p {{
  white-space: normal;
  overflow: visible;
  text-overflow: clip;
}}

.stButton > button:hover,
.stDownloadButton > button:hover {{
  background: var(--sc-surface-3);
  border-color: var(--sc-border-strong);
  color: var(--sc-text);
}}

.stButton > button:focus-visible,
.stDownloadButton > button:focus-visible {{
  outline: 2px solid var(--sc-primary);
  outline-offset: 2px;
}}

/* ---------- Panels ---------- */

[data-testid="stExpander"] {{
  background: var(--sc-surface);
  border: 1px solid var(--sc-border);
  border-radius: var(--sc-radius);
}}

[data-testid="stExpander"] summary {{ font-size: .875rem; color: var(--sc-text-muted); }}
[data-testid="stExpander"] summary:hover {{ color: var(--sc-text); }}

[data-testid="stDataFrame"] {{
  border: 1px solid var(--sc-border);
  border-radius: var(--sc-radius);
  overflow: hidden;
}}

/* ---------- Motion preferences ---------- */

@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{
    animation-duration: .001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .001ms !important;
  }}
}}

/* ---------- Small screens ---------- */

@media (max-width: 640px) {{
  .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
  .sc-hero {{ padding-top: 2rem; }}
  .sc-orb {{ width: 84px; height: 84px; }}
  [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {{
    max-width: 92%;
  }}
}}
</style>
"""


def inject_styles() -> None:
    st.markdown(STYLES, unsafe_allow_html=True)


def greeting(now: datetime | None = None) -> str:
    """Time-of-day greeting, matching how a person would open the day."""
    hour = (now or datetime.now()).hour
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


def render_hero(name: str = "Analyst") -> None:
    st.markdown(
        f"""
        <div class="sc-hero">
          <div class="sc-orb" role="img" aria-label="Startup Chatbot assistant"></div>
          <h1 class="sc-hero__greeting">
            {greeting()}, {name}.<br>Can I help you with anything?
          </h1>
          <p class="sc-hero__sub">
            Describe the startups you are looking for — sector, geography, funding
            stage, revenue — and I will research them and build a downloadable report.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
