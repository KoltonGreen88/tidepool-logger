import json
import time
from datetime import date, datetime

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


def _table_base(file_id: str) -> str:
    site_id = st.secrets["SHAREPOINT_SITE_ID"]
    return (
        f"https://graph.microsoft.com/v1.0/sites/{site_id}"
        f"/drive/items/{file_id}/workbook/tables"
    )


def append_row(file_id: str, table_name: str, values: list) -> bool:
    url = f"{_table_base(file_id)}/{table_name}/rows/add"
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
gifting_tab, event_tab, creator_tab = st.tabs(["Gifting Log", "Event Wrap-Up", "Creator Applications"])


# ═══════════════════════════════════════════════════════════════════════════════
# GIFTING TAB
# ═══════════════════════════════════════════════════════════════════════════════
with gifting_tab:

    if st.session_state["g_success"]:
        st.success(st.session_state["g_success"])
        st.session_state["g_success"] = ""

    st.markdown("### Log a Gift")

    # ── AI parse ──────────────────────────────────────────────────────────────
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

    # ── Gifting form ──────────────────────────────────────────────────────────
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
