import json
import time
import traceback
from datetime import date, datetime, timedelta

import anthropic
import requests
import streamlit as st
from dateutil import parser as dateparser

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TIDEPOOL Logger",
    page_icon="🌊",
    layout="centered",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700&family=Barlow:wght@400;500;600&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Barlow', sans-serif !important;
    background-color: #1C2B4A !important;
    color: #E8EAF0 !important;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Barlow Condensed', sans-serif !important;
    color: #E8C94A !important;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* Buttons */
.stButton > button {
    background-color: #E8C94A !important;
    color: #1C2B4A !important;
    font-family: 'Barlow Condensed', sans-serif !important;
    text-transform: uppercase !important;
    font-size: 18px !important;
    font-weight: 700 !important;
    min-height: 52px !important;
    width: 100% !important;
    border: none !important;
    border-radius: 8px !important;
    cursor: pointer !important;
    letter-spacing: 1px;
}
.stButton > button:hover,
.stButton > button:active,
.stButton > button:focus,
.stButton > button:focus-visible {
    background-color: #d4b43a !important;
    color: #1C2B4A !important;
    outline: none !important;
    box-shadow: none !important;
}

/* Text inputs */
.stTextInput > div > div > input {
    background-color: #243350 !important;
    border: 1px solid #3a4f70 !important;
    color: #E8EAF0 !important;
    border-radius: 8px !important;
}
/* Number inputs */
.stNumberInput > div > div > input {
    background-color: #243350 !important;
    border: 1px solid #3a4f70 !important;
    color: #E8EAF0 !important;
    border-radius: 8px !important;
}
/* Text areas */
.stTextArea > div > div > textarea {
    background-color: #243350 !important;
    border: 1px solid #3a4f70 !important;
    color: #E8EAF0 !important;
    border-radius: 8px !important;
}
/* Select boxes */
.stSelectbox > div > div {
    background-color: #243350 !important;
    border: 1px solid #3a4f70 !important;
    color: #E8EAF0 !important;
    border-radius: 8px !important;
}
/* Date inputs */
.stDateInput > div > div > input {
    background-color: #243350 !important;
    border: 1px solid #3a4f70 !important;
    color: #E8EAF0 !important;
    border-radius: 8px !important;
}

/* Form containers */
div[data-testid="stForm"] {
    background-color: #243350 !important;
    border: 1px solid #3a4f70 !important;
    border-radius: 12px !important;
    padding: 20px !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background-color: #1C2B4A !important;
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Barlow Condensed', sans-serif !important;
    text-transform: uppercase !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    color: #E8EAF0 !important;
    background-color: #243350 !important;
    border-radius: 6px 6px 0 0 !important;
    padding: 8px 20px !important;
}
.stTabs [aria-selected="true"] {
    background-color: #E8C94A !important;
    color: #1C2B4A !important;
}

/* Labels */
label, .stRadio label, .stCheckbox label {
    color: #E8EAF0 !important;
    font-family: 'Barlow', sans-serif !important;
}
/* Radio option text (Streamlit renders these as <p> inside <label>) */
div[data-testid="stRadio"] label p,
div[data-testid="stRadio"] label div,
div[data-testid="stRadio"] p {
    color: #E8EAF0 !important;
}
/* Checkbox label text */
div[data-testid="stCheckbox"] label p,
div[data-testid="stCheckbox"] label span,
div[data-testid="stCheckbox"] p {
    color: #E8EAF0 !important;
}
/* Form widget labels (text_input, number_input, text_area, selectbox, date_input) */
div[data-testid="stTextInput"] label,
div[data-testid="stNumberInput"] label,
div[data-testid="stTextArea"] label,
div[data-testid="stSelectbox"] label,
div[data-testid="stDateInput"] label,
div[data-testid="stSelectbox"] label p,
div[data-testid="stTextInput"] label p,
div[data-testid="stNumberInput"] label p,
div[data-testid="stTextArea"] label p,
div[data-testid="stDateInput"] label p {
    color: #E8EAF0 !important;
}
/* Tooltips and hover popups */
div[data-testid="stTooltipIcon"],
div[data-testid="stTooltipContent"],
div[data-testid="stTooltipContent"] p,
[data-baseweb="tooltip"],
[data-baseweb="tooltip"] p {
    color: #E8EAF0 !important;
    background-color: #243350 !important;
}

/* Dividers */
hr { border-color: #3a4f70 !important; }

/* Caption / helper text */
.stCaption, small { color: #8090b0 !important; }
</style>
""",
    unsafe_allow_html=True,
)

# ── Graph API helpers ─────────────────────────────────────────────────────────


def get_graph_token() -> str:
    """Return a cached Graph API token, fetching a new one if expired."""
    now = time.time()
    if (
        "graph_token" in st.session_state
        and st.session_state.get("graph_token_expiry", 0) > now + 60
    ):
        return st.session_state["graph_token"]

    resp = requests.post(
        f"https://login.microsoftonline.com/{st.secrets['GRAPH_TENANT_ID']}/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": st.secrets["GRAPH_CLIENT_ID"],
            "client_secret": st.secrets["GRAPH_CLIENT_SECRET"],
            "scope": "https://graph.microsoft.com/.default",
        },
        timeout=15,
    )
    if resp.status_code != 200:
        st.error(f"Auth error {resp.status_code}: {resp.text}")
        st.stop()

    data = resp.json()
    st.session_state["graph_token"] = data["access_token"]
    st.session_state["graph_token_expiry"] = now + data.get("expires_in", 3600)
    return st.session_state["graph_token"]


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {get_graph_token()}",
        "Content-Type": "application/json",
    }


def _table_base(file_id: str, site_id: str | None = None) -> str:
    _site = site_id or st.secrets["SHAREPOINT_SITE_ID"]
    return (
        f"https://graph.microsoft.com/v1.0/sites/{_site}"
        f"/drive/items/{file_id}/workbook/tables"
    )


def append_row(file_id: str, table_name: str, values: list, site_id: str | None = None) -> bool:
    url = f"{_table_base(file_id, site_id)}/{table_name}/rows/add"
    try:
        resp = requests.post(url, headers=_headers(), json={"values": [values]}, timeout=20)
        if resp.status_code not in (200, 201):
            st.error(f"Append error {resp.status_code}: {resp.text}")
            return False
        return True
    except Exception as exc:
        st.error(f"Request failed: {exc}")
        return False


def get_table_rows(file_id: str, table_name: str) -> list:
    url = f"{_table_base(file_id)}/{table_name}/rows"
    try:
        resp = requests.get(url, headers=_headers(), timeout=20)
        if resp.status_code == 404:
            return []
        if resp.status_code != 200:
            st.error(f"Fetch error {resp.status_code}: {resp.text}")
            return []
        return resp.json().get("value", [])
    except Exception as exc:
        st.error(f"Request failed: {exc}")
        return []


def patch_row(file_id: str, table_name: str, row_index: int, values: list) -> bool:
    url = f"{_table_base(file_id)}/{table_name}/rows/itemAt(index={row_index})"
    try:
        resp = requests.patch(url, headers=_headers(), json={"values": [values]}, timeout=20)
        if resp.status_code not in (200, 204):
            st.error(f"Patch error {resp.status_code}: {resp.text}")
            return False
        return True
    except Exception as exc:
        st.error(f"Request failed: {exc}")
        return False


# ── Utility helpers ───────────────────────────────────────────────────────────

_PLATFORM_MAP = [
    ("instagram.com", "Instagram"),
    ("tiktok.com", "TikTok"),
    ("youtube.com", "YouTube"),
    ("youtu.be", "YouTube"),
    ("facebook.com", "Facebook"),
    ("twitter.com", "Twitter/X"),
    ("x.com", "Twitter/X"),
    ("linkedin.com", "LinkedIn"),
    ("pinterest.com", "Pinterest"),
]


def detect_content_type(url: str) -> str:
    if not url:
        return ""
    u = url.lower()
    for domain, label in _PLATFORM_MAP:
        if domain in u:
            return label
    return "Other"


def parse_with_ai(text: str) -> dict:
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    today = date.today().isoformat()
    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Today is {today}. Extract gifting information from the text below. "
                    "Return ONLY a JSON object with exactly these keys: "
                    "recipient (string), bags (integer), venue (string), "
                    "date (string YYYY-MM-DD — default to today if not specified), "
                    "notes (string — empty string if none). No markdown, no explanation.\n\n"
                    f"Text: {text}"
                ),
            }
        ],
    )
    raw = msg.content[0].text.strip()
    # Strip markdown code fences if Claude wraps them
    if "```" in raw:
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    return json.loads(raw)


# ── Capture Review helpers ────────────────────────────────────────────────────

def _strip_json(raw: str) -> str:
    if "```" in raw:
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    return raw.strip()


def _fetch_granola_meetings() -> list | None:
    key = st.secrets.get("GRANOLA_API_KEY", "paste-your-value-here")
    if not key or key == "paste-your-value-here":
        return None
    created_after = (
        (datetime.utcnow() - timedelta(days=30))
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    try:
        resp = requests.get(
            "https://public-api.granola.ai/v1/notes",
            headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
            params={"created_after": created_after},
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        notes = data.get("notes", [])
        notes_sorted = sorted(notes, key=lambda n: n.get("created_at", ""), reverse=True)
        result = []
        for n in notes_sorted[:10]:
            raw_date = n.get("created_at", "")
            try:
                parsed_dt = dateparser.parse(raw_date)
                friendly_date = parsed_dt.strftime("%-d %b %Y") if parsed_dt else raw_date[:10]
            except Exception:
                friendly_date = raw_date[:10]
            result.append({
                "id": n.get("id", ""),
                "title": n.get("title", "(untitled)"),
                "date": friendly_date,
            })
        return result
    except Exception:
        return None


def _fetch_granola_content(meeting_id: str) -> dict:
    """Returns dict with keys: content, data_source, needs_review, review_reason."""
    key = st.secrets.get("GRANOLA_API_KEY", "paste-your-value-here")
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    try:
        resp = requests.get(
            f"https://public-api.granola.ai/v1/notes/{meeting_id}",
            headers=headers,
            params={"include": "transcript"},
            timeout=20,
        )
        if resp.status_code != 200:
            return {"content": "", "data_source": "manual", "needs_review": True,
                    "review_reason": f"Granola API returned {resp.status_code}"}
        data = resp.json()
        transcript_items = data.get("transcript") or []
        if transcript_items:
            lines = []
            for item in transcript_items:
                speaker = (
                    item.get("speaker", {}).get("source")
                    or item.get("diarization_label")
                    or "Speaker"
                )
                text = item.get("text", "").strip()
                if text:
                    lines.append(f"{speaker}: {text}")
            content = "\n".join(lines)
            if content.strip():
                return {"content": content, "data_source": "transcript",
                        "needs_review": False, "review_reason": ""}
        summary = data.get("summary") or data.get("notes") or ""
        if summary:
            return {
                "content": summary,
                "data_source": "summary",
                "needs_review": True,
                "review_reason": (
                    "Extracted from AI summary not verbatim transcript - "
                    "verify bags, pricing, and commitment details before confirming"
                ),
            }
        return {"content": "", "data_source": "manual", "needs_review": True,
                "review_reason": "No transcript or summary available for this note"}
    except Exception as exc:
        return {"content": "", "data_source": "manual", "needs_review": True,
                "review_reason": f"Error fetching Granola content: {exc}"}


def extract_meeting(content: str, data_source: str, meeting_type: str = "External Meeting") -> dict:
    _sys = (
        "You are the TIDEPOOL Capture Agent extracting structured meeting data for "
        "SharePoint storage. TIDEPOOL is a glutathione and electrolyte recovery drink "
        "mix brand based in Atlanta. Founded January 2026. DTC $24.99. B2B landed cost "
        "$11.31. Wholesale tiers: Starter 12 bags $18.99, Growth 18 bags $17.49, Partner "
        "24 bags $15.99. Target venues: medspas, recovery studios, wellness studios, "
        "gyms, corporate accounts. Founders: Kolton Green (science/creative/medically "
        "adjacent venues) and Cameron Kopp (relationship/sales/community venues). "
        "Single shared Granola account - assigned_founder determined by transcript context "
        "using personas above. Default to Kolton if unclear. "
        f"This meeting is classified as: {meeting_type}. "
        "Never invent data. Return null for any field not clearly present. "
        "Never use em dashes. Return valid JSON only. No prose. No markdown."
    )
    _usr = (
        "Extract meeting data and return JSON with these exact fields: "
        "contact_name, contact_title, venue_name, "
        "venue_type (one of: Medspa / Recovery Studio / Wellness Studio / Gym / "
        "Corporate / Hotel / Event / Other), meeting_date (YYYY-MM-DD), "
        "assigned_founder (Kolton or Cameron), "
        "opportunity_type (one of: Wholesale / Gifting / Partnership / Event / "
        "Investor / Press / Other), "
        "bags_gifted (integer or null), bags_sold (integer or null), "
        "revenue (dollar amount as string or null), "
        "stage (one of: First Contact / Follow-up / Proposal Sent / Verbal Yes / "
        "Closed / Pass), "
        "key_insight (one sentence - most important outcome of this meeting), "
        "follow_up_items (array of strings, each a specific action with owner if mentioned), "
        "wholesale_potential (high / medium / low / null), "
        "franchise_flag (true if franchise or multi-location ownership mentioned else false), "
        "notes (anything important not captured above). "
        "Wholesale potential: high = decision maker present + pricing discussed + interest; "
        "medium = interested but gatekeeper or needs follow-up with owner; "
        "low = casual interest, no decision maker, no next step. "
        f"Meeting content: {content}"
    )
    ac = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    msg = ac.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        system=_sys,
        messages=[{"role": "user", "content": _usr}],
    )
    return json.loads(_strip_json(msg.content[0].text))


def _transcribe_video_mcp(url: str) -> dict | None:
    u = url.lower()
    if "tiktok.com" in u:
        _tool = "get_tiktok_transcript"
        _platform = "TikTok"
    elif "instagram.com" in u:
        _tool = "get_instagram_transcript"
        _platform = "Instagram"
    elif "youtube.com" in u or "youtu.be" in u:
        _tool = "get_youtube_transcript"
        _platform = "YouTube"
    else:
        _tool = "get_tiktok_transcript"
        _platform = "Other"
    try:
        _resp = requests.post(
            "https://api.tokscript.com/mcp",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Authorization": "Bearer " + st.secrets.get("TOKSCRIPT_API_KEY", ""),
            },
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": _tool, "arguments": {"video_url": url, "format": "text"}},
                "id": 1,
            },
            timeout=60,
            stream=True,
        )
        _result = None
        _first_data = None
        for _line in _resp.iter_lines():
            if isinstance(_line, bytes):
                _line = _line.decode("utf-8")
            if not _line.startswith("data:"):
                continue
            _raw_chunk = _line[len("data:"):].strip()
            if _first_data is None:
                _first_data = _raw_chunk
            _parsed = json.loads(_raw_chunk)
            if "result" in _parsed:
                _result = _parsed["result"]
                break
        if _result is None:
            return None
        _data = json.loads(_result["content"][0]["text"])
        _pub = _data.get("publishDate") or ""
        return {
            "transcript": _data.get("transcript") or "",
            "creator_handle": (_data.get("author") or {}).get("username") or None,
            "creator_name": (_data.get("author") or {}).get("displayName") or None,
            "video_date": _pub[:10] if _pub else None,
            "platform": _platform,
            "title": _data.get("title") or None,
        }
    except Exception:
        return None


def extract_video(transcript: str, url: str, platform: str, saved_by: str) -> dict:
    _sys = (
        "You are the TIDEPOOL Capture Agent extracting structured video idea data for "
        "SharePoint storage. TIDEPOOL is a glutathione and electrolyte recovery drink "
        "mix brand based in Atlanta. Founded January 2026. DTC $24.99. "
        "Never invent data. Return null for any field not clearly present. "
        "Never use em dashes. Return valid JSON only. No prose. No markdown."
    )
    _usr = (
        "Extract video idea data and return JSON with these exact fields: "
        f"source_url (use: {url}), "
        f"platform (use: {platform}), "
        "creator_handle (@handle if visible or null), "
        "creator_name (full name if mentioned or null), "
        "video_date (YYYY-MM-DD if determinable or null), "
        f"saved_by (use: {saved_by}), "
        "key_idea (one sentence - the core insight or concept most relevant to TIDEPOOL), "
        "tidepool_relevance (one of: Product / Content / AI-Tools / Business / "
        "Wholesale / Events / Gifting), "
        "relevance_reasoning (one sentence - why this is relevant to TIDEPOOL specifically), "
        "recommended_action (one of: SWIPE / ADAPT / REFERENCE / SHARE - "
        "SWIPE=pure inspiration save for reference, ADAPT=take concept make it TIDEPOOL, "
        "REFERENCE=cite or share internally, SHARE=repost or amplify as-is), "
        "action_reasoning (one sentence - why this specific action), "
        "content_hook (if tidepool_relevance is Content extract the hook or opening line "
        "verbatim else null), "
        "tactical_takeaway (one sentence on what TIDEPOOL could directly steal or adapt from "
        "this video — specific and actionable, not generic). "
        f"Transcript: {transcript}"
    )
    ac = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    msg = ac.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=_sys,
        messages=[{"role": "user", "content": _usr}],
    )
    return json.loads(_strip_json(msg.content[0].text))


def _get_pending_rows(file_id: str, table_name: str) -> list:
    """Returns list of (row_index, values_list) for rows where status == 'pending'."""
    rows = get_table_rows(file_id, table_name)
    out = []
    for r in rows:
        vals = r.get("values", [[]])[0] if r.get("values") else []
        idx = r.get("index", 0)
        if vals and str(vals[-3]).lower() == "pending":
            out.append((idx, vals))
    return out


# ── Session state defaults ────────────────────────────────────────────────────

_DEFAULTS = {
    "authed": False,
    "g_parsed": {},
    "g_success": "",
    "e_pre_success": "",
    "e_post_success": "",
    "c_success": "",
    "parsed_applicants": None,
    "ai_recommendation": None,
    "recommendation_overrides": {},
    "ca_gen": 0,
    "ca_logged_campaigns": set(),
    "g_search_results": None,
    "cap_success": "",
    "cap_gen": 0,
    "cap_mtg_list": None,
    "cap_mtg_extracted": None,
    "cap_last_mtg_id": None,
    "cap_vid_extracted": None,
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Password gate ─────────────────────────────────────────────────────────────

if not st.session_state["authed"]:
    st.markdown(
        """
        <div style="text-align:center; padding:60px 0 24px;">
            <div style="font-family:'Barlow Condensed',sans-serif; font-size:52px; font-weight:700;
                        color:#E8C94A; text-transform:uppercase; letter-spacing:5px;">
                🌊 TIDEPOOL
            </div>
            <div style="font-family:'Barlow',sans-serif; font-size:14px; color:#8090b0; margin-top:6px;">
                Field Logging System
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        pwd = st.text_input("Password", type="password", label_visibility="hidden",
                            placeholder="Password")
        if st.button("Enter →"):
            if pwd == st.secrets["APP_PASSWORD"]:
                st.session_state["authed"] = True
                st.rerun()
            else:
                st.error("Incorrect password.")
    st.stop()

# ── App header ────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div style="text-align:center; padding:20px 0 12px;">
        <div style="font-family:'Barlow Condensed',sans-serif; font-size:38px; font-weight:700;
                    color:#E8C94A; text-transform:uppercase; letter-spacing:4px;">
            🌊 TIDEPOOL Logger
        </div>
        <div style="font-family:'Barlow',sans-serif; font-size:13px; color:#8090b0; margin-top:4px;">
            Inventory Gifting &amp; Event Activity
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Tabs ──────────────────────────────────────────────────────────────────────
gifting_tab, event_tab, creator_tab, capture_tab = st.tabs(["Gifting Log", "Event Wrap-Up", "Creator Applications", "📥 Capture Review"])


# ═══════════════════════════════════════════════════════════════════════════════
# GIFTING TAB
# ═══════════════════════════════════════════════════════════════════════════════
with gifting_tab:

    if st.session_state["g_success"]:
        st.success(st.session_state["g_success"])
        st.session_state["g_success"] = ""

    st.markdown("### Log a Gift")
    g_mode = st.radio(
        "Mode",
        ["Log New Gift", "Update Existing Record"],
        horizontal=True,
        key="g_mode",
        label_visibility="collapsed",
    )
    st.markdown("---")

    # ── MODE: Log New Gift ────────────────────────────────────────────────────
    if g_mode == "Log New Gift":

        # ── AI parse ──────────────────────────────────────────────────────────
        parse_text = st.text_area(
            "Describe the gifting — AI will pre-fill the form below",
            height=80,
            placeholder="e.g. Dropped off 3 bags at Exhale Spa for Sarah on May 30th",
            key="g_parse_input",
        )
        if st.button("Parse with AI →", key="parse_btn"):
            if not parse_text.strip():
                st.warning("Enter a description first.")
            else:
                with st.spinner("Parsing..."):
                    try:
                        st.session_state["g_parsed"] = parse_with_ai(parse_text)
                        st.rerun()
                    except Exception as exc:
                        st.error(f"AI parse failed: {exc}")

        parsed = st.session_state["g_parsed"]

        # ── Gifting form ──────────────────────────────────────────────────────
        # GiftingLog columns:
        # Timestamp | Recipient | Bags | Venue | Date | LoggedBy | Notes | Posted | PostLink | ContentType
        with st.form("gifting_form", clear_on_submit=True):
            recipient = st.text_input(
                "Recipient *",
                value=parsed.get("recipient", ""),
                placeholder="Name, handle, or contact",
            )
            bags = st.number_input(
                "Bags *",
                min_value=0,
                step=1,
                value=max(0, int(parsed.get("bags") or 0)),
            )
            venue = st.text_input(
                "Venue *",
                value=parsed.get("venue", ""),
                placeholder="Studio, spa, hotel, event space…",
            )

            default_date = date.today()
            if parsed.get("date"):
                try:
                    default_date = dateparser.parse(str(parsed["date"])).date()
                except Exception:
                    pass
            gift_date = st.date_input("Date *", value=default_date)

            logged_by = st.radio("Logged By *", ["Kolton", "Cameron"], horizontal=True)

            notes = st.text_area(
                "Notes",
                value=str(parsed.get("notes", "") or ""),
                placeholder="Context, relationship, follow-up needed…",
                height=80,
            )

            posted = st.checkbox("They posted")
            post_link = st.text_input(
                "Post Link",
                placeholder="https://instagram.com/p/…",
                help="Only recorded when 'Posted' is checked.",
            )
            st.caption("Content type (Instagram, TikTok, etc.) is auto-detected from the URL on submit.")

            submitted = st.form_submit_button("Log Gift →")

        if submitted:
            errors = []
            if not recipient.strip():
                errors.append("Recipient is required.")
            if bags <= 0:
                errors.append("Bags must be at least 1.")
            if not venue.strip():
                errors.append("Venue is required.")

            if errors:
                for err in errors:
                    st.error(err)
            else:
                used_link = post_link.strip() if posted else ""
                content_type = detect_content_type(used_link) if used_link else ""
                timestamp = datetime.now().isoformat(timespec="seconds")
                row = [
                    timestamp,
                    recipient.strip(),
                    int(bags),
                    venue.strip(),
                    gift_date.isoformat(),
                    logged_by,
                    notes.strip(),
                    "Yes" if posted else "No",
                    used_link,
                    content_type,
                ]
                with st.spinner("Saving to SharePoint…"):
                    ok = append_row(st.secrets["GIFTING_FILE_ID"], "GiftingLog", row)
                if ok:
                    st.session_state["g_success"] = (
                        f"Logged: {recipient.strip()} · {int(bags)} bags · "
                        f"{venue.strip()} · {gift_date.isoformat()}"
                    )
                    st.session_state["g_parsed"] = {}
                    st.rerun()

    # ── MODE: Update Existing Record ──────────────────────────────────────────
    else:

        # ── Search ────────────────────────────────────────────────────────────
        g_search_q = st.text_input("Search recipient name", key="g_search_q")
        if st.button("Search →", key="g_search_btn"):
            if not g_search_q.strip():
                st.warning("Enter a name to search.")
            else:
                with st.spinner("Searching SharePoint…"):
                    _all_rows = get_table_rows(st.secrets["GIFTING_FILE_ID"], "GiftingLog")
                _matches = [
                    r for r in _all_rows
                    if g_search_q.strip().lower() in str(r.get("values", [[]])[0][1] if r.get("values") else "").lower()
                ]
                st.session_state["g_search_results"] = _matches
                st.rerun()

        _results = st.session_state.get("g_search_results")

        if _results is not None:
            if not _results:
                st.info("No matching records found.")
            else:
                # GiftingLog column positions: 0=Timestamp 1=Recipient 2=Bags 3=Venue 4=Date
                #                              5=LoggedBy 6=Notes 7=Posted 8=PostLink 9=ContentType
                _opts = [
                    f"{r['values'][0][1]} · {r['values'][0][3]} · {r['values'][0][4]}"
                    for r in _results
                ]
                _sel_i = st.selectbox(
                    "Select record to edit",
                    range(len(_opts)),
                    format_func=lambda i: _opts[i],
                    key="g_sel_idx",
                )
                _row = _results[_sel_i]
                _vals = _row["values"][0]
                _row_index = _row["index"]

                st.markdown("---")

                # Read-only fields
                st.text_input("Recipient", value=str(_vals[1]), disabled=True)
                st.text_input("Venue", value=str(_vals[3]), disabled=True)
                st.text_input("Content Type", value=str(_vals[9] or ""), disabled=True)

                # Editable fields
                _edit_bags = st.number_input(
                    "Bags", min_value=0, step=1,
                    value=max(0, int(_vals[2]) if str(_vals[2]).isdigit() else 0),
                    key="g_edit_bags",
                )
                _edit_date_default = date.today()
                try:
                    _edit_date_default = dateparser.parse(str(_vals[4])).date()
                except Exception:
                    pass
                _edit_date = st.date_input("Date", value=_edit_date_default, key="g_edit_date")

                _lb_options = ["Kolton", "Cameron"]
                _lb_idx = 1 if str(_vals[5]) == "Cameron" else 0
                _edit_logged_by = st.radio(
                    "Logged By", _lb_options, index=_lb_idx,
                    horizontal=True, key="g_edit_logged_by",
                )
                _edit_notes = st.text_area(
                    "Notes", value=str(_vals[6] or ""), height=80, key="g_edit_notes",
                )
                _edit_posted = st.checkbox(
                    "They posted", value=(str(_vals[7]).strip().lower() == "yes"),
                    key="g_edit_posted",
                )
                _edit_post_link = st.text_input(
                    "Post Link", value=str(_vals[8] or ""), key="g_edit_post_link",
                )
                _edit_used_link = _edit_post_link.strip() if _edit_posted else ""
                _edit_content_type = detect_content_type(_edit_used_link) if _edit_used_link else str(_vals[9] or "")
                st.caption(f"Content type: {_edit_content_type or '(none)'}")

                if st.button("Update Record →", key="g_update_btn"):
                    _updated_row = [
                        _vals[0],
                        _vals[1],
                        int(_edit_bags),
                        _vals[3],
                        _edit_date.isoformat(),
                        _edit_logged_by,
                        _edit_notes.strip(),
                        "Yes" if _edit_posted else "No",
                        _edit_used_link,
                        _edit_content_type,
                    ]
                    with st.spinner("Updating SharePoint…"):
                        ok = patch_row(
                            st.secrets["GIFTING_FILE_ID"], "GiftingLog",
                            _row_index, _updated_row,
                        )
                    if ok:
                        st.session_state["g_success"] = (
                            f"Updated: {_vals[1]} · {int(_edit_bags)} bags · {_edit_date.isoformat()}"
                        )
                        st.session_state["g_search_results"] = None
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# EVENT TAB
# ═══════════════════════════════════════════════════════════════════════════════
with event_tab:

    if st.session_state["e_pre_success"]:
        st.success(st.session_state["e_pre_success"])
        st.session_state["e_pre_success"] = ""
    if st.session_state["e_post_success"]:
        st.success(st.session_state["e_post_success"])
        st.session_state["e_post_success"] = ""

    st.markdown("### Event Tracking")

    event_mode = st.radio(
        "Mode",
        ["Pre-Event", "Post-Event"],
        horizontal=True,
        key="event_mode_radio",
    )

    # ── Pre-Event ─────────────────────────────────────────────────────────────
    if event_mode == "Pre-Event":
        st.markdown("#### Pre-Event Details")

        # EventLog columns:
        # Timestamp | Venue | VenueType | EventDate | BagsAllocated | LoggedBy |
        # Sampled | Sold | Leads | Followups | Notes | Status
        with st.form("pre_event_form", clear_on_submit=True):
            e_venue = st.text_input("Venue *", placeholder="Studio, spa, hotel name")
            e_venue_type = st.selectbox(
                "Venue Type *",
                ["Hotel/Luxury", "Wellness Studio", "Med Spa", "Recovery/Sports", "Corporate", "Other"],
            )
            e_event_date = st.date_input("Event Date *", value=date.today())
            e_bags = st.number_input("Bags Allocated *", min_value=0, step=1, value=0)
            e_logged_by = st.radio("Logged By *", ["Kolton", "Cameron"], horizontal=True,
                                   key="pre_logged_by")

            pre_submit = st.form_submit_button("Pre-Log Event →")

        if pre_submit:
            errors = []
            if not e_venue.strip():
                errors.append("Venue is required.")
            if e_bags <= 0:
                errors.append("Bags Allocated must be at least 1.")

            if errors:
                for err in errors:
                    st.error(err)
            else:
                timestamp = datetime.now().isoformat(timespec="seconds")
                row = [
                    timestamp,
                    e_venue.strip(),
                    e_venue_type,
                    e_event_date.isoformat(),
                    int(e_bags),
                    e_logged_by,
                    0,            # Sampled
                    0,            # Sold
                    0,            # Leads
                    0,            # Followups
                    "",           # Notes
                    "Pre-logged", # Status
                ]
                with st.spinner("Saving to SharePoint…"):
                    ok = append_row(st.secrets["EVENTS_FILE_ID"], "EventLog", row)
                if ok:
                    st.session_state["e_pre_success"] = (
                        f"Pre-logged: {e_venue.strip()} on {e_event_date.isoformat()}"
                    )
                    st.rerun()

    # ── Post-Event ────────────────────────────────────────────────────────────
    else:
        st.markdown("#### Post-Event Wrap-Up")

        post_mode = st.radio(
            "Post-event type",
            ["Select pre-logged event", "Log standalone post-event"],
            horizontal=True,
            key="post_mode_radio",
            label_visibility="collapsed",
        )
        st.markdown("---")

        # ── Sub-mode: Select pre-logged event (existing behaviour unchanged) ──
        if post_mode == "Select pre-logged event":

            with st.spinner("Loading pre-logged events…"):
                all_rows = get_table_rows(st.secrets["EVENTS_FILE_ID"], "EventLog")

            # Row structure: [0]Timestamp [1]Venue [2]VenueType [3]EventDate
            #   [4]BagsAllocated [5]LoggedBy [6]Sampled [7]Sold
            #   [8]Leads [9]Followups [10]Notes [11]Status
            pre_logged = []
            for row_obj in all_rows:
                vals = row_obj.get("values", [[]])[0] if row_obj.get("values") else []
                if len(vals) > 11 and vals[11] == "Pre-logged":
                    pre_logged.append((row_obj.get("index", 0), vals))

            if not pre_logged:
                st.info("No pre-logged events yet. Switch to Pre-Event mode to log upcoming events.")
            else:
                labels = [f"{v[1]} — {v[3]}" for _, v in pre_logged]
                sel = st.selectbox(
                    "Select Event *",
                    range(len(labels)),
                    format_func=lambda i: labels[i],
                    key="post_event_selector",
                )
                row_index, row_vals = pre_logged[sel]

                with st.form("post_event_form", clear_on_submit=True):
                    sampled = st.number_input("Sampled", min_value=0, step=1, value=0)
                    sold = st.number_input("Sold", min_value=0, step=1, value=0)
                    leads = st.number_input("Leads", min_value=0, step=1, value=0)
                    followups = st.number_input("Followups", min_value=0, step=1, value=0)
                    post_notes = st.text_area(
                        "Notes",
                        placeholder="Event highlights, feedback, follow-ups needed…",
                        height=100,
                    )

                    post_submit = st.form_submit_button("Complete Event →")

                if post_submit:
                    updated_row = [
                        row_vals[0],         # Timestamp (original, preserve)
                        row_vals[1],         # Venue
                        row_vals[2],         # VenueType
                        row_vals[3],         # EventDate
                        row_vals[4],         # BagsAllocated
                        row_vals[5],         # LoggedBy
                        int(sampled),
                        int(sold),
                        int(leads),
                        int(followups),
                        post_notes.strip(),
                        "Complete",
                    ]
                    with st.spinner("Updating SharePoint…"):
                        ok = patch_row(st.secrets["EVENTS_FILE_ID"], "EventLog", row_index, updated_row)
                    if ok:
                        st.session_state["e_post_success"] = (
                            f"Completed: {row_vals[1]} — {row_vals[3]}"
                        )
                        st.rerun()

        # ── Sub-mode: Log standalone post-event ───────────────────────────────
        else:
            _venue_type_opts = [
                "Hotel/Luxury", "Wellness Studio", "Med Spa",
                "Recovery/Sports", "Corporate", "Other",
            ]
            with st.form("standalone_post_event_form", clear_on_submit=True):
                sp_venue = st.text_input("Venue *", placeholder="Studio, spa, hotel name")
                sp_venue_type = st.selectbox("Venue Type *", _venue_type_opts)
                sp_event_date = st.date_input("Event Date *", value=date.today())
                sp_bags = st.number_input("Bags Allocated *", min_value=0, step=1, value=0)
                sp_sampled = st.number_input("Sampled", min_value=0, step=1, value=0)
                sp_sold = st.number_input("Sold", min_value=0, step=1, value=0)
                sp_leads = st.number_input("Leads", min_value=0, step=1, value=0)
                sp_followups = st.number_input("Followups", min_value=0, step=1, value=0)
                sp_logged_by = st.radio(
                    "Logged By *", ["Kolton", "Cameron"],
                    horizontal=True, key="sp_logged_by",
                )
                sp_notes = st.text_area(
                    "Notes",
                    placeholder="Event highlights, feedback, follow-ups needed…",
                    height=100,
                )
                sp_submit = st.form_submit_button("Log Event →")

            if sp_submit:
                sp_errors = []
                if not sp_venue.strip():
                    sp_errors.append("Venue is required.")
                if sp_bags <= 0:
                    sp_errors.append("Bags Allocated must be at least 1.")

                if sp_errors:
                    for err in sp_errors:
                        st.error(err)
                else:
                    sp_row = [
                        datetime.now().isoformat(timespec="seconds"),
                        sp_venue.strip(),
                        sp_venue_type,
                        sp_event_date.isoformat(),
                        int(sp_bags),
                        sp_logged_by,
                        int(sp_sampled),
                        int(sp_sold),
                        int(sp_leads),
                        int(sp_followups),
                        sp_notes.strip(),
                        "Complete",
                    ]
                    with st.spinner("Saving to SharePoint…"):
                        ok = append_row(st.secrets["EVENTS_FILE_ID"], "EventLog", sp_row)
                    if ok:
                        st.session_state["e_post_success"] = (
                            f"Logged: {sp_venue.strip()} — {sp_event_date.isoformat()}"
                        )
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# CREATOR APPLICATIONS TAB
# ═══════════════════════════════════════════════════════════════════════════════
with creator_tab:

    if st.session_state["c_success"]:
        st.success(st.session_state["c_success"])
        st.session_state["c_success"] = ""

    st.markdown("### Creator Applications")

    # Generation counter — incrementing resets all widget keys in this tab
    _gen = st.session_state["ca_gen"]

    # ── Section A — Campaign Setup (always visible) ───────────────────────────
    st.markdown("#### Campaign Setup")
    ca_campaign = st.text_input(
        "Campaign Name",
        placeholder="e.g. June 2026 Wave 1",
        key=f"ca_campaign_{_gen}",
    )
    ca_platform = st.selectbox(
        "Platform",
        ["Roeme", "Direct", "Other"],
        key=f"ca_platform_{_gen}",
    )
    ca_target = st.number_input(
        "Target Selections",
        min_value=1,
        step=1,
        value=3,
        key=f"ca_target_{_gen}",
    )
    ca_logged_by = st.radio(
        "Logged By",
        ["Kolton", "Cameron"],
        horizontal=True,
        key=f"ca_logged_by_{_gen}",
    )
    ca_hist_import = st.checkbox(
        "Historical Import (skip AI recommendation)",
        key=f"ca_hist_{_gen}",
    )

    st.markdown("---")

    # ── Section B — Step 1: Paste and Parse ───────────────────────────────────
    st.markdown("#### Step 1 — Paste & Parse Applicants")

    _raw_input = st.text_area(
        "Paste raw applicant text from Roeme here",
        height=200,
        placeholder="Paste the full applicant batch text here…",
        key=f"ca_raw_{_gen}",
    )

    if st.button("Parse with AI →", key=f"ca_parse_{_gen}"):
        if not _raw_input.strip():
            st.warning("Paste applicant text before parsing.")
        else:
            _raw_resp = ""
            with st.spinner("Parsing applicants…"):
                try:
                    _ac = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
                    _amsg = _ac.messages.create(
                        model="claude-sonnet-4-5",
                        max_tokens=10000,
                        messages=[{
                            "role": "user",
                            "content": (
                                "Extract creator application data from this raw text and return ONLY "
                                "a valid JSON array with no markdown or code fences. Each applicant "
                                "object must contain: name (string), instagram_followers (integer or null), "
                                "tiktok_followers (integer or null), application_response (full verbatim text), "
                                "status (string, default pending). If a field is not present return null. "
                                f"Raw text: {_raw_input}"
                            ),
                        }],
                    )
                    _raw_resp = _amsg.content[0].text.strip()
                    if "```" in _raw_resp:
                        _fp = _raw_resp.split("```")
                        _raw_resp = _fp[1] if len(_fp) > 1 else _raw_resp
                        if _raw_resp.lower().startswith("json"):
                            _raw_resp = _raw_resp[4:].strip()
                    _parsed_list = json.loads(_raw_resp)
                    st.session_state["parsed_applicants"] = _parsed_list
                    st.session_state["ai_recommendation"] = None
                    st.session_state["recommendation_overrides"] = {}
                    st.rerun()
                except json.JSONDecodeError as _je:
                    st.error(f"JSON parse failed: {_je}\n\nRaw API response:\n{_raw_resp}")
                except Exception as _exc:
                    st.error(f"AI parse failed: {_exc}")

    # ── Editable preview + Steps 2–3 (shown only after successful parse) ──────
    _parsed = st.session_state.get("parsed_applicants")

    if _parsed:
        st.caption(f"{len(_parsed)} applicant(s) parsed. Review and edit below, then run Step 2.")

        # Build display rows (Application Response truncated to 100 chars)
        _display_rows = []
        for _a in _parsed:
            _display_rows.append({
                "Name": _a.get("name", ""),
                "Instagram": _a.get("instagram_followers"),
                "TikTok": _a.get("tiktok_followers"),
                "Application Response": (str(_a.get("application_response", "") or ""))[:100],
                "Status": _a.get("status", "pending"),
            })

        _edited = st.data_editor(
            _display_rows,
            column_config={
                "Instagram": st.column_config.NumberColumn("Instagram Followers", min_value=0),
                "TikTok": st.column_config.NumberColumn("TikTok Followers", min_value=0),
                "Application Response": st.column_config.TextColumn(
                    "Application Response (preview)",
                    disabled=True,
                    width="large",
                ),
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["pending", "selected", "waitlist", "pass"],
                    required=True,
                ),
            },
            use_container_width=True,
            num_rows="fixed",
            hide_index=True,
            key=f"ca_editor_{_gen}",
        )

        st.markdown("---")

        if ca_hist_import:
            # ── Historical Import — bulk status + confirm (no AI) ─────────────
            st.markdown("#### Confirm & Log Historical Import")
            _bulk_status = st.selectbox(
                "Set all statuses to",
                ["pending", "selected", "waitlist", "pass", "complete", "closed"],
                index=4,
                key=f"ca_bulk_status_{_gen}",
            )

            if st.button("Confirm and Log Import →", key=f"ca_confirm_{_gen}"):
                if not ca_campaign.strip():
                    st.error("Campaign name is required before logging.")
                else:
                    _ts = datetime.now().isoformat(timespec="seconds")
                    _had_error = False
                    _skipped = []
                    _written = 0
                    _logged_set = st.session_state["ca_logged_campaigns"]

                    with st.spinner("Logging historical import…"):
                        for _a in _parsed:
                            _name = _a.get("name", "")
                            _dedup_key = f"{ca_campaign.strip()}|{_name}"
                            if _dedup_key in _logged_set:
                                _skipped.append(_name)
                                continue
                            _creator_row = [
                                _ts,
                                ca_campaign.strip(),
                                ca_platform,
                                _name,
                                _a.get("instagram_followers"),
                                _a.get("tiktok_followers"),
                                _a.get("application_response", ""),
                                _bulk_status,
                                0,
                                "",
                                "",
                                "",
                                ca_logged_by,
                            ]
                            if not append_row(
                                st.secrets["CREATOR_FILE_ID"], "CreatorApplications", _creator_row
                            ):
                                _had_error = True
                            else:
                                _logged_set.add(_dedup_key)
                                _written += 1

                    if _skipped:
                        st.warning(f"Skipped {len(_skipped)} duplicate(s) already logged this session: {', '.join(_skipped)}")
                    if not _had_error:
                        st.session_state["c_success"] = (
                            f"Historical import logged — {_written} applicants recorded as '{_bulk_status}'."
                        )
                        for _key in ["parsed_applicants", "ai_recommendation",
                                     "recommendation_overrides"]:
                            st.session_state.pop(_key, None)
                        st.session_state["ca_gen"] += 1
                        st.rerun()

        else:
            # ── Section C — Step 2: AI Recommendation ─────────────────────────
            st.markdown("#### Step 2 — AI Recommendation")

            if st.button("Get AI Recommendation →", key=f"ca_rec_{_gen}"):
                # Normalize editor return (list of dicts or DataFrame)
                if hasattr(_edited, "to_dict"):
                    _edited_rows = _edited.to_dict("records")
                else:
                    _edited_rows = list(_edited)

                # Merge editor values with original full application_response text
                _full_for_ai = []
                for _i, _row in enumerate(_edited_rows):
                    _orig_a = _parsed[_i] if _i < len(_parsed) else {}
                    _full_for_ai.append({
                        "name": _row.get("Name", _orig_a.get("name", "")),
                        "instagram_followers": _row.get("Instagram", _orig_a.get("instagram_followers")),
                        "tiktok_followers": _row.get("TikTok", _orig_a.get("tiktok_followers")),
                        "application_response": _orig_a.get("application_response", ""),
                        "status": _row.get("Status", _orig_a.get("status", "pending")),
                    })

                _ai_json = json.dumps(_full_for_ai)
                _raw_resp = ""
                with st.spinner("Analyzing applicants…"):
                    try:
                        _ac = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
                        _amsg = _ac.messages.create(
                            model="claude-sonnet-4-5",
                            max_tokens=15000,
                            messages=[{
                                "role": "user",
                                "content": (
                                    "You are selecting creators for a TIDEPOOL gifting campaign. "
                                    "TIDEPOOL is a glutathione and electrolyte recovery drink mix brand "
                                    "based in Atlanta. DTC price $24.99. Target audience: wellness-oriented "
                                    "25-35 year olds. Inventory is limited so selections must be high conviction.\n\n"
                                    f"Select ONLY the top {int(ca_target)} applicants as tier 'selected'. "
                                    "All others must be 'waitlist' or 'pass'. This limit is strict.\n\n"
                                    "Score each applicant and recommend based on:\n"
                                    "1. Authenticity — do they describe a real personal use case or is it generic?\n"
                                    "2. Content angle — is there a clear natural content story (recovery, Sunday reset, post-workout, travel)?\n"
                                    "3. Audience fit — does their audience match the TIDEPOOL wellness demographic?\n"
                                    "4. Reach vs engagement — authentic voice matters more than raw follower count at nano level\n"
                                    "5. Wholesale potential — does their venue, profession, or platform suggest a future wholesale relationship?\n\n"
                                    "Return ONLY a valid JSON object with no markdown and no code fences in this exact structure:\n"
                                    '{"campaign_summary": "three sentences on what this cohort signals about TIDEPOOL perception and one content theme to brief them all on", '
                                    '"applicants": [{"name": "string", "tier": "selected or waitlist or pass", "score": "integer 1-10", '
                                    '"reasoning": "two sentences max specific to their application", '
                                    '"content_angle": "one sentence on what their content would look like", '
                                    '"wholesale_flag": "true or false"}]}\n\n'
                                    f"Sort applicants array by score descending. Applicants: {_ai_json}"
                                ),
                            }],
                        )
                        _raw_resp = _amsg.content[0].text.strip()
                        if "```" in _raw_resp:
                            _fp = _raw_resp.split("```")
                            _raw_resp = _fp[1] if len(_fp) > 1 else _raw_resp
                            if _raw_resp.lower().startswith("json"):
                                _raw_resp = _raw_resp[4:].strip()
                        _ai_result = json.loads(_raw_resp)
                        st.session_state["ai_recommendation"] = _ai_result
                        st.session_state["recommendation_overrides"] = {}
                        st.rerun()
                    except json.JSONDecodeError as _je:
                        st.error(f"JSON parse failed: {_je}\n\nRaw API response:\n{_raw_resp}")
                    except Exception as _exc:
                        st.error(f"AI recommendation failed: {_exc}")

            # ── Recommendation display (shown after Step 2 completes) ──────────
            _ai_rec = st.session_state.get("ai_recommendation")

            if _ai_rec:
                _summary = _ai_rec.get("campaign_summary", "")
                _rec_apps = _ai_rec.get("applicants", [])

                # Campaign signal card
                st.markdown(
                    f"""
                    <div style="background:#1D9E75; border-radius:10px; padding:16px; margin-bottom:16px;">
                        <div style="font-family:'Barlow Condensed',sans-serif; font-size:16px;
                                    font-weight:700; color:white; text-transform:uppercase;
                                    letter-spacing:1px; margin-bottom:8px;">Campaign Signal</div>
                        <div style="color:white; font-size:14px; line-height:1.6;">{_summary}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                _tier_border = {"selected": "#1D9E75", "waitlist": "#E8C94A", "pass": "#3a4f70"}
                _tier_text = {"selected": "white", "waitlist": "#1C2B4A", "pass": "white"}
                _status_opts = ["selected", "waitlist", "pass"]

                for _i, _app in enumerate(_rec_apps):
                    _name = _app.get("name", "")
                    _score = _app.get("score", 0)
                    _tier = str(_app.get("tier", "pass")).lower()
                    _reasoning = _app.get("reasoning", "")
                    _angle = _app.get("content_angle", "")
                    _wholesale = _app.get("wholesale_flag", False)
                    _bc = _tier_border.get(_tier, "#3a4f70")
                    _tc = _tier_text.get(_tier, "white")

                    _ws_html = (
                        '<span style="background:#D85A30; color:white; font-size:12px; '
                        'padding:2px 8px; border-radius:4px; font-weight:600; margin-left:4px;">'
                        "WHOLESALE POTENTIAL</span>"
                    ) if _wholesale else ""

                    st.markdown(
                        f"""
                        <div style="background:#243350; border-left:4px solid {_bc};
                                    border-radius:10px; padding:16px; margin-bottom:4px;">
                            <div style="display:flex; align-items:center; flex-wrap:wrap;
                                        gap:8px; margin-bottom:10px;">
                                <span style="font-family:'Barlow Condensed',sans-serif; font-size:18px;
                                             font-weight:700; color:#E8C94A;">{_name}</span>
                                <span style="background:#5B6FA8; color:white; padding:2px 10px;
                                             border-radius:4px; font-size:13px; font-weight:600;">{_score}/10</span>
                                <span style="background:{_bc}; color:{_tc}; padding:2px 10px;
                                             border-radius:4px; font-size:12px; font-weight:700;
                                             text-transform:uppercase;">{_tier}</span>
                                {_ws_html}
                            </div>
                            <div style="color:#E8EAF0; font-size:14px; margin-bottom:8px;
                                        line-height:1.5;">{_reasoning}</div>
                            <div style="color:#8090b0; font-size:13px; font-style:italic;
                                        line-height:1.5;">{_angle}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Status override selectbox pre-filled from AI tier
                    _cur = st.session_state.get(f"ca_ov_{_gen}_{_i}", _tier)
                    _ov_idx = _status_opts.index(_cur) if _cur in _status_opts else 0
                    st.selectbox(
                        f"Status for {_name}",
                        _status_opts,
                        index=_ov_idx,
                        key=f"ca_ov_{_gen}_{_i}",
                        label_visibility="collapsed",
                    )

                st.markdown("---")

                # ── Section D — Step 3: Confirm and Log ───────────────────────
                st.markdown("#### Step 3 — Confirm & Log Campaign")

                if st.button("Confirm and Log Campaign →", key=f"ca_confirm_{_gen}"):
                    if not ca_campaign.strip():
                        st.error("Campaign name is required before logging.")
                    else:
                        _ts = datetime.now().isoformat(timespec="seconds")
                        _td = date.today().isoformat()
                        _counts = {"selected": 0, "waitlist": 0, "pass": 0}
                        _had_error = False

                        for _i, _app in enumerate(_rec_apps):
                            _name = _app.get("name", "")
                            # Read status from override selectbox; fall back to AI tier
                            _final = st.session_state.get(
                                f"ca_ov_{_gen}_{_i}", _app.get("tier", "pass")
                            )
                            # Match original parsed record by name for follower counts + full response
                            _pm = next(
                                (p for p in (_parsed or [])
                                 if p.get("name", "").lower() == _name.lower()),
                                {},
                            )
                            _creator_row = [
                                _ts,
                                ca_campaign.strip(),
                                ca_platform,
                                _name,
                                _pm.get("instagram_followers"),
                                _pm.get("tiktok_followers"),
                                _pm.get("application_response", ""),
                                _final,
                                _app.get("score", 0),
                                _app.get("reasoning", ""),
                                _app.get("content_angle", ""),
                                str(_app.get("wholesale_flag", False)),
                                ca_logged_by,
                            ]
                            if not append_row(
                                st.secrets["CREATOR_FILE_ID"], "CreatorApplications", _creator_row
                            ):
                                _had_error = True

                            _sk = _final if _final in _counts else "pass"
                            _counts[_sk] += 1

                            if _final == "selected":
                                _gifting_row = [
                                    _ts,
                                    _name,
                                    "",
                                    "Roeme Application",
                                    _td,
                                    ca_logged_by,
                                    f"Auto-created from {ca_campaign.strip()} creator selection",
                                    "No",
                                    "",
                                    "",
                                ]
                                if not append_row(
                                    st.secrets["GIFTING_FILE_ID"], "GiftingLog", _gifting_row
                                ):
                                    _had_error = True

                        if not _had_error:
                            _n = len(_rec_apps)
                            st.session_state["c_success"] = (
                                f"Logged {_n} applicants — {_counts['selected']} selected, "
                                f"{_counts['waitlist']} waitlisted, {_counts['pass']} passed. "
                                f"{_counts['selected']} gifting records pre-created."
                            )
                            for _key in ["parsed_applicants", "ai_recommendation",
                                         "recommendation_overrides"]:
                                st.session_state.pop(_key, None)
                            st.session_state["ca_gen"] += 1
                            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# CAPTURE REVIEW TAB
# ═══════════════════════════════════════════════════════════════════════════════
with capture_tab:

    if st.session_state["cap_success"]:
        st.success(st.session_state["cap_success"])
        st.session_state["cap_success"] = ""

    st.markdown("### Capture Review")

    _cgen = st.session_state["cap_gen"]

    cap_mode = st.radio(
        "Capture type",
        ["Meeting Capture", "Video Idea"],
        horizontal=True,
        key="cap_mode_radio",
        label_visibility="collapsed",
    )
    st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════════
    # MEETING CAPTURE
    # ═══════════════════════════════════════════════════════════════════════
    if cap_mode == "Meeting Capture":
        st.markdown("#### Meeting Capture")

        # ── Step 1: Meeting type + load or paste meeting content ──────────
        _mtg_type_opts = ["External Meeting", "Founder Discussion", "Event Audio", "Other"]
        _mtg_type = st.selectbox(
            "Meeting Type",
            _mtg_type_opts,
            index=0,
            key=f"cap_mtg_type_{_cgen}",
        )

        _mtg_list = st.session_state.get("cap_mtg_list")
        _granola_configured = (
            st.secrets.get("GRANOLA_API_KEY", "paste-your-value-here")
            not in ("paste-your-value-here", "")
        )

        if _granola_configured:
            if st.button("Load Recent Meetings from Granola →", key=f"cap_load_{_cgen}"):
                with st.spinner("Fetching from Granola..."):
                    _fetched = _fetch_granola_meetings()
                st.session_state["cap_mtg_list"] = _fetched if _fetched is not None else []
                st.rerun()

        _show_paste = (not _granola_configured) or (_mtg_list is not None and len(_mtg_list) == 0)
        _meeting_id = None
        _meeting_meta = {}

        if _mtg_list and not _show_paste:
            # Granola dropdown
            _mtg_opts = [f"{m.get('title','(untitled)')} — {m.get('date','')}" for m in _mtg_list]
            _sel_i = st.selectbox(
                "Select a recent meeting",
                range(len(_mtg_opts)),
                format_func=lambda i: _mtg_opts[i],
                key=f"cap_mtg_sel_{_cgen}",
            )
            _meeting_id = _mtg_list[_sel_i].get("id")
            _meeting_meta = _mtg_list[_sel_i]
            _paste_content = ""
            _manual_date = None

            # Clear previous extraction when user switches to a different meeting
            if _meeting_id != st.session_state.get("cap_last_mtg_id"):
                st.session_state["cap_last_mtg_id"] = _meeting_id
                st.session_state["cap_mtg_extracted"] = None
        else:
            if _granola_configured and _mtg_list is not None:
                st.info("No recent meetings found in Granola.")
            st.markdown("**Paste meeting content:**")
            _paste_content = st.text_area(
                "Transcript or summary",
                height=200,
                placeholder="Paste Granola export, transcript, or meeting notes here...",
                key=f"cap_mtg_paste_{_cgen}",
            )
            _manual_date = st.date_input("Meeting date", value=date.today(), key=f"cap_mtg_date_{_cgen}")

        # ── Step 2: Extract ────────────────────────────────────────────────
        if st.button("Extract with AI →", key=f"cap_mtg_extract_{_cgen}"):
            _content = ""
            _data_source = "manual"
            _needs_review = False
            _review_reason = ""

            if _meeting_id:
                with st.spinner("Fetching transcript..."):
                    _gc = _fetch_granola_content(_meeting_id)
                    _content = _gc["content"]
                    _data_source = _gc["data_source"]
                    _needs_review = _gc["needs_review"]
                    _review_reason = _gc["review_reason"]
                if not _content:
                    st.error("Could not retrieve meeting content from Granola. Paste content manually below.")
                    st.stop()
            else:
                _content = _paste_content.strip()
                _data_source = "manual"
                _needs_review = True
                _review_reason = "Manually pasted content - verify all fields"

            if not _content:
                st.warning("No meeting content to extract from.")
            else:
                with st.spinner("Extracting fields..."):
                    try:
                        _extracted = extract_meeting(_content, _data_source, _mtg_type)
                        _extracted["data_source"] = _data_source
                        _extracted["meeting_type"] = _mtg_type
                        _extracted["needs_review"] = _needs_review
                        _extracted["review_reason"] = _review_reason
                        _extracted["status"] = "pending"
                        _extracted["timestamp"] = datetime.now().isoformat(timespec="seconds")
                        if _manual_date and not _extracted.get("meeting_date"):
                            _extracted["meeting_date"] = _manual_date.isoformat()
                        st.session_state["cap_mtg_extracted"] = _extracted
                        st.rerun()
                    except json.JSONDecodeError as _je:
                        st.error(f"Extraction parse error: {_je}")
                    except Exception as _exc:
                        st.error(f"Extraction failed: {_exc}")

        # ── Step 3: Confirm card ───────────────────────────────────────────
        _mtg_ext = st.session_state.get("cap_mtg_extracted")

        if _mtg_ext:
            _nr = _mtg_ext.get("needs_review", False)
            if _nr:
                st.markdown(
                    '<div style="background:#D85A30; border-radius:8px; padding:10px 16px; '
                    'margin-bottom:12px; color:white; font-size:14px; font-weight:600;">'
                    "⚠ Some fields may need verification — extracted from summary, not full transcript"
                    "</div>",
                    unsafe_allow_html=True,
                )
            st.markdown("**MEETING CAPTURE — Review & Confirm**")
            st.caption(
                f"Contact: {_mtg_ext.get('contact_name','—')} · {_mtg_ext.get('venue_name','—')} | "
                f"Meeting: {_mtg_ext.get('meeting_type','—')} | "
                f"Type: {_mtg_ext.get('opportunity_type','—')} | "
                f"Assigned: {_mtg_ext.get('assigned_founder','—')} | "
                f"Follow-ups: {len(_mtg_ext.get('follow_up_items') or [])} items"
            )

            with st.expander("Edit all fields"):
                _mtg_ext["contact_name"] = st.text_input("Contact Name", value=str(_mtg_ext.get("contact_name") or ""), key=f"ce_cn_{_cgen}")
                _mtg_ext["contact_title"] = st.text_input("Contact Title", value=str(_mtg_ext.get("contact_title") or ""), key=f"ce_ct_{_cgen}")
                _mtg_ext["venue_name"] = st.text_input("Venue Name", value=str(_mtg_ext.get("venue_name") or ""), key=f"ce_vn_{_cgen}")
                _vt_opts = ["Medspa", "Recovery Studio", "Wellness Studio", "Gym", "Corporate", "Hotel", "Event", "Other"]
                _vt_cur = _mtg_ext.get("venue_type", "Other")
                _vt_idx = _vt_opts.index(_vt_cur) if _vt_cur in _vt_opts else len(_vt_opts) - 1
                _mtg_ext["venue_type"] = st.selectbox("Venue Type", _vt_opts, index=_vt_idx, key=f"ce_vtype_{_cgen}")
                _md_val = date.today()
                try:
                    _md_val = dateparser.parse(str(_mtg_ext.get("meeting_date",""))).date()
                except Exception:
                    pass
                _mtg_ext["meeting_date"] = st.date_input("Meeting Date", value=_md_val, key=f"ce_md_{_cgen}").isoformat()
                _af_opts = ["Kolton", "Cameron"]
                _af_idx = 1 if _mtg_ext.get("assigned_founder") == "Cameron" else 0
                _mtg_ext["assigned_founder"] = st.radio("Assigned Founder", _af_opts, index=_af_idx, horizontal=True, key=f"ce_af_{_cgen}")
                _ot_opts = ["Wholesale", "Gifting", "Partnership", "Event", "Investor", "Press", "Other"]
                _ot_cur = _mtg_ext.get("opportunity_type", "Other")
                _ot_idx = _ot_opts.index(_ot_cur) if _ot_cur in _ot_opts else len(_ot_opts) - 1
                _mtg_ext["opportunity_type"] = st.selectbox("Opportunity Type", _ot_opts, index=_ot_idx, key=f"ce_ot_{_cgen}")
                _mtg_ext["bags_gifted"] = st.number_input("Bags Gifted", min_value=0, step=1, value=int(_mtg_ext.get("bags_gifted") or 0), key=f"ce_bg_{_cgen}")
                _mtg_ext["bags_sold"] = st.number_input("Bags Sold", min_value=0, step=1, value=int(_mtg_ext.get("bags_sold") or 0), key=f"ce_bs_{_cgen}")
                _mtg_ext["revenue"] = st.text_input("Revenue", value=str(_mtg_ext.get("revenue") or ""), key=f"ce_rev_{_cgen}")
                _st_opts = ["First Contact", "Follow-up", "Proposal Sent", "Verbal Yes", "Closed", "Pass"]
                _st_cur = _mtg_ext.get("stage", "First Contact")
                _st_idx = _st_opts.index(_st_cur) if _st_cur in _st_opts else 0
                _mtg_ext["stage"] = st.selectbox("Stage", _st_opts, index=_st_idx, key=f"ce_stage_{_cgen}")
                _mtg_ext["key_insight"] = st.text_area("Key Insight", value=str(_mtg_ext.get("key_insight") or ""), height=80, key=f"ce_ki_{_cgen}")
                _fu_raw = "\n".join(_mtg_ext.get("follow_up_items") or [])
                _fu_edited = st.text_area("Follow-up Items (one per line)", value=_fu_raw, height=100, key=f"ce_fu_{_cgen}")
                _mtg_ext["follow_up_items"] = [l.strip() for l in _fu_edited.splitlines() if l.strip()]
                _wp_opts = ["high", "medium", "low", "null"]
                _wp_cur = str(_mtg_ext.get("wholesale_potential") or "null")
                _wp_idx = _wp_opts.index(_wp_cur) if _wp_cur in _wp_opts else 3
                _mtg_ext["wholesale_potential"] = st.selectbox("Wholesale Potential", _wp_opts, index=_wp_idx, key=f"ce_wp_{_cgen}")
                _mtg_ext["franchise_flag"] = st.checkbox("Franchise / Multi-location flag", value=bool(_mtg_ext.get("franchise_flag")), key=f"ce_ff_{_cgen}")
                _mtg_ext["notes"] = st.text_area("Notes", value=str(_mtg_ext.get("notes") or ""), height=80, key=f"ce_notes_{_cgen}")
                _lb_opts = ["Kolton", "Cameron"]
                _lb_idx = 1 if _mtg_ext.get("logged_by") == "Cameron" else 0
                _mtg_ext["logged_by"] = st.radio("Logged By", _lb_opts, index=_lb_idx, horizontal=True, key=f"ce_lb_{_cgen}")

            if st.button("Log to SharePoint →", key=f"cap_mtg_log_{_cgen}"):
                _fu_str = "; ".join(_mtg_ext.get("follow_up_items") or [])
                _mtg_row = [
                    _mtg_ext.get("timestamp", datetime.now().isoformat(timespec="seconds")),
                    str(_mtg_ext.get("meeting_type") or ""),
                    str(_mtg_ext.get("contact_name") or ""),
                    str(_mtg_ext.get("contact_title") or ""),
                    str(_mtg_ext.get("venue_name") or ""),
                    str(_mtg_ext.get("venue_type") or ""),
                    str(_mtg_ext.get("meeting_date") or ""),
                    str(_mtg_ext.get("assigned_founder") or ""),
                    str(_mtg_ext.get("opportunity_type") or ""),
                    _mtg_ext.get("bags_gifted") or 0,
                    _mtg_ext.get("bags_sold") or 0,
                    str(_mtg_ext.get("revenue") or ""),
                    str(_mtg_ext.get("stage") or ""),
                    str(_mtg_ext.get("key_insight") or ""),
                    _fu_str,
                    str(_mtg_ext.get("wholesale_potential") or ""),
                    str(_mtg_ext.get("franchise_flag", False)),
                    str(_mtg_ext.get("notes") or ""),
                    str(_mtg_ext.get("data_source") or ""),
                    str(_mtg_ext.get("needs_review", False)),
                    str(_mtg_ext.get("review_reason") or ""),
                    "pending",
                    str(_mtg_ext.get("logged_by") or "Kolton"),
                ]
                with st.spinner("Saving to SharePoint..."):
                    _ok = append_row(st.secrets["MEETINGS_FILE_ID"], "MeetingLog", _mtg_row,
                                    site_id=st.secrets["STRATEGY_SITE_ID"])
                if _ok:
                    st.session_state["cap_success"] = (
                        f"Meeting captured: {_mtg_ext.get('contact_name','—')} - "
                        f"{_mtg_ext.get('venue_name','—')} (pending confirmation)"
                    )
                    st.session_state["cap_mtg_extracted"] = None
                    st.session_state["cap_mtg_list"] = None
                    st.session_state["cap_gen"] += 1
                    st.rerun()

    # ═══════════════════════════════════════════════════════════════════════
    # VIDEO IDEA CAPTURE
    # ═══════════════════════════════════════════════════════════════════════
    else:
        st.markdown("#### Video Idea Capture")

        _vid_url = st.text_input(
            "Paste video URL",
            placeholder="https://www.tiktok.com/@handle/video/...",
            key=f"cap_vid_url_{_cgen}",
        )
        _vid_saved_by = st.radio("Saved by", ["Kolton", "Cameron"], horizontal=True, key=f"cap_vid_sb_{_cgen}")

        def _detect_platform(url: str) -> str:
            u = url.lower()
            if "tiktok.com" in u:
                return "TikTok"
            if "instagram.com" in u:
                return "Instagram"
            if "youtube.com" in u or "youtu.be" in u:
                return "YouTube"
            return "Other"

        _vid_platform = _detect_platform(_vid_url) if _vid_url else ""
        if _vid_platform:
            st.caption(f"Platform detected: {_vid_platform}")

        _show_manual_transcript = st.session_state.get("cap_vid_show_paste", False)
        _manual_transcript = ""
        if _show_manual_transcript:
            st.warning("Could not transcribe this video. Paste transcript manually below.")
            _manual_transcript = st.text_area(
                "Paste transcript or caption text",
                height=200,
                key=f"cap_vid_paste_{_cgen}",
            )

        if st.button("Extract with AI →", key=f"cap_vid_extract_{_cgen}"):
            if not _vid_url.strip():
                st.warning("Paste a video URL first.")
            else:
                _mcp_data = None
                _transcript = None
                if not _show_manual_transcript:
                    with st.spinner("Fetching transcript..."):
                        _mcp_data = _transcribe_video_mcp(_vid_url.strip())
                    if _mcp_data is None:
                        st.session_state["cap_vid_show_paste"] = True
                        st.rerun()
                    else:
                        _transcript = _mcp_data.get("transcript")

                _transcript_text = _transcript or _manual_transcript
                if not _transcript_text.strip():
                    st.warning("No transcript content to extract from.")
                else:
                    with st.spinner("Extracting fields..."):
                        try:
                            _vext = extract_video(
                                _transcript_text, _vid_url.strip(),
                                _vid_platform, _vid_saved_by,
                            )
                            if _mcp_data:
                                for _k in ("creator_handle", "creator_name", "video_date", "platform"):
                                    if _mcp_data.get(_k):
                                        _vext[_k] = _mcp_data[_k]
                            _vext["status"] = "pending"
                            _vext["timestamp"] = datetime.now().isoformat(timespec="seconds")
                            st.session_state["cap_vid_extracted"] = _vext
                            st.session_state["cap_vid_show_paste"] = False
                            st.rerun()
                        except json.JSONDecodeError as _je:
                            st.error(f"Extraction parse error: {_je}")
                        except Exception as _exc:
                            st.error(f"Extraction failed: {_exc}")

        _vid_ext = st.session_state.get("cap_vid_extracted")

        if _vid_ext:
            _act_colors = {"SWIPE": "#5B6FA8", "ADAPT": "#1D9E75", "REFERENCE": "#E8C94A", "SHARE": "#D85A30"}
            _act = str(_vid_ext.get("recommended_action", "SWIPE"))
            _act_color = _act_colors.get(_act, "#5B6FA8")
            st.markdown(
                f"""
                <div style="background:#243350; border-left:4px solid {_act_color};
                            border-radius:10px; padding:16px; margin-bottom:12px;">
                    <div style="font-family:'Barlow Condensed',sans-serif; font-size:13px;
                                font-weight:700; color:#8090b0; text-transform:uppercase;
                                letter-spacing:1px; margin-bottom:8px;">VIDEO CAPTURE</div>
                    <div style="color:#E8C94A; font-size:16px; font-weight:700;
                                margin-bottom:4px;">{_vid_ext.get('platform','')}: {_vid_ext.get('creator_handle') or _vid_url[:40]}</div>
                    <div style="color:#E8EAF0; font-size:14px; margin-bottom:4px;">
                        {_vid_ext.get('key_idea','')}</div>
                    <div style="color:#8090b0; font-size:13px; margin-bottom:8px;">
                        {_vid_ext.get('tidepool_relevance','')} · Saved by {_vid_ext.get('saved_by','')}</div>
                    <span style="background:{_act_color}; color:white; padding:3px 10px;
                                 border-radius:4px; font-size:12px; font-weight:700;">
                        {_act}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.expander("Edit all fields"):
                _vid_ext["creator_handle"] = st.text_input("Creator Handle", value=str(_vid_ext.get("creator_handle") or ""), key=f"ve_ch_{_cgen}")
                _vid_ext["creator_name"] = st.text_input("Creator Name", value=str(_vid_ext.get("creator_name") or ""), key=f"ve_cnm_{_cgen}")
                _rel_opts = ["Product", "Content", "AI-Tools", "Business", "Wholesale", "Events", "Gifting"]
                _rel_cur = _vid_ext.get("tidepool_relevance", "Content")
                _rel_idx = _rel_opts.index(_rel_cur) if _rel_cur in _rel_opts else 0
                _vid_ext["tidepool_relevance"] = st.selectbox("TIDEPOOL Relevance", _rel_opts, index=_rel_idx, key=f"ve_rel_{_cgen}")
                _vid_ext["key_idea"] = st.text_area("Key Idea", value=str(_vid_ext.get("key_idea") or ""), height=80, key=f"ve_ki_{_cgen}")
                _vid_ext["relevance_reasoning"] = st.text_area("Relevance Reasoning", value=str(_vid_ext.get("relevance_reasoning") or ""), height=60, key=f"ve_rr_{_cgen}")
                _ra_opts = ["SWIPE", "ADAPT", "REFERENCE", "SHARE"]
                _ra_cur = _vid_ext.get("recommended_action", "SWIPE")
                _ra_idx = _ra_opts.index(_ra_cur) if _ra_cur in _ra_opts else 0
                _vid_ext["recommended_action"] = st.selectbox("Recommended Action", _ra_opts, index=_ra_idx, key=f"ve_ra_{_cgen}")
                _vid_ext["action_reasoning"] = st.text_area("Action Reasoning", value=str(_vid_ext.get("action_reasoning") or ""), height=60, key=f"ve_ar_{_cgen}")
                _vid_ext["content_hook"] = st.text_input("Content Hook", value=str(_vid_ext.get("content_hook") or ""), key=f"ve_hook_{_cgen}")

            if st.button("Log to SharePoint →", key=f"cap_vid_log_{_cgen}"):
                _vid_row = [
                    str(_vid_ext.get("source_url") or ""),
                    str(_vid_ext.get("platform") or ""),
                    str(_vid_ext.get("creator_handle") or ""),
                    str(_vid_ext.get("creator_name") or ""),
                    str(_vid_ext.get("video_date") or ""),
                    str(_vid_ext.get("saved_by") or ""),
                    str(_vid_ext.get("key_idea") or ""),
                    str(_vid_ext.get("tidepool_relevance") or ""),
                    str(_vid_ext.get("relevance_reasoning") or ""),
                    str(_vid_ext.get("recommended_action") or ""),
                    str(_vid_ext.get("action_reasoning") or ""),
                    str(_vid_ext.get("content_hook") or ""),
                    str(_vid_ext.get("tactical_takeaway") or ""),
                    "pending",
                    _vid_ext.get("timestamp", datetime.now().isoformat(timespec="seconds")),
                    str(_vid_ext.get("saved_by") or "Kolton"),
                ]
                with st.spinner("Saving to SharePoint..."):
                    _ok = append_row(st.secrets["VIDEO_FILE_ID"], "VideoIdeas", _vid_row,
                                    site_id=st.secrets["STRATEGY_SITE_ID"])
                if _ok:
                    st.session_state["cap_success"] = (
                        f"Video captured: {_vid_ext.get('platform','')} - "
                        f"{_vid_ext.get('creator_handle') or 'unknown'} (pending confirmation)"
                    )
                    st.session_state["cap_vid_extracted"] = None
                    st.session_state["cap_vid_show_paste"] = False
                    st.session_state["cap_gen"] += 1
                    st.rerun()

    # ═══════════════════════════════════════════════════════════════════════
    # PENDING QUEUE
    # ═══════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("#### Pending Queue")

    _mtg_pending = []
    _vid_pending = []
    _mtg_fid = st.secrets.get("MEETINGS_FILE_ID", "paste-your-value-here")
    _vid_fid = st.secrets.get("VIDEO_FILE_ID", "paste-your-value-here")

    if _mtg_fid not in ("paste-your-value-here", ""):
        with st.spinner("Loading pending captures..."):
            _mtg_pending = _get_pending_rows(_mtg_fid, "MeetingLog")
    if _vid_fid not in ("paste-your-value-here", ""):
        _vid_pending = _get_pending_rows(_vid_fid, "VideoIdeas")

    _all_pending = (
        [("meeting", ri, v) for ri, v in _mtg_pending] +
        [("video", ri, v) for ri, v in _vid_pending]
    )
    _all_pending.sort(key=lambda x: x[2][-2] if len(x[2]) >= 2 else "", reverse=True)

    if not _all_pending:
        st.caption("No pending captures. All confirmed.")
    else:
        st.caption(f"{len(_all_pending)} pending capture(s) awaiting confirmation.")

        if st.button("Confirm All →", key="cap_confirm_all"):
            _errs = 0
            for _ptype, _ri, _pvals in _all_pending:
                _new_vals = list(_pvals)
                _new_vals[-3] = "confirmed"
                _fid = _mtg_fid if _ptype == "meeting" else _vid_fid
                _tbl = "MeetingLog" if _ptype == "meeting" else "VideoIdeas"
                if not patch_row(_fid, _tbl, _ri, _new_vals):
                    _errs += 1
            if _errs == 0:
                st.session_state["cap_success"] = f"Confirmed {len(_all_pending)} captures."
            else:
                st.warning(f"{_errs} error(s) during batch confirm.")
            st.rerun()

        for _ptype, _ri, _pvals in _all_pending:
            if _ptype == "meeting":
                _icon = "🤝"
                _label = f"{_pvals[0] or '—'} · {_pvals[2] or '—'} · {_pvals[4] or '—'}"
                _sub = f"Assigned: {_pvals[5] or '—'}"
                _fid = _mtg_fid
                _tbl = "MeetingLog"
            else:
                _icon = "🎬"
                _label = f"{_pvals[1] or '—'}: {_pvals[2] or _pvals[0][:30] or '—'}"
                _sub = f"Action: {_pvals[9] or '—'} · Saved by: {_pvals[5] or '—'}"
                _fid = _vid_fid
                _tbl = "VideoIdeas"

            _pc1, _pc2, _pc3 = st.columns([5, 1, 1])
            with _pc1:
                st.markdown(f"**{_icon} {_label}**  \n{_sub}")
            with _pc2:
                if st.button("Confirm", key=f"cap_conf_{_ptype}_{_ri}"):
                    _new_vals = list(_pvals)
                    _new_vals[-3] = "confirmed"
                    with st.spinner("Confirming..."):
                        patch_row(_fid, _tbl, _ri, _new_vals)
                    st.rerun()
            with _pc3:
                if st.button("Discard", key=f"cap_disc_{_ptype}_{_ri}"):
                    _new_vals = list(_pvals)
                    _new_vals[-3] = "discarded"
                    with st.spinner("Discarding..."):
                        patch_row(_fid, _tbl, _ri, _new_vals)
                    st.rerun()
