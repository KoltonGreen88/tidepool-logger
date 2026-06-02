# TIDEPOOL Logger

Mobile-first Streamlit web app for two founders to log inventory gifting and event activity. Every submission writes directly to Excel tables in SharePoint via Microsoft Graph API — the Excel files are the permanent source of truth.

---

## Prerequisites

- Python 3.9+
- A Microsoft 365 / Azure account with SharePoint access
- Admin rights to grant Azure API permissions (or an admin who can do it)
- An Anthropic API key (for AI-assisted gifting parse)

---

## 1 — Azure App Registration

### 1.1 Register the app

1. Open [Azure Portal](https://portal.azure.com) → search **App registrations** → **New registration**
2. Fill in:
   - **Name**: `Tidepool Logger` (or anything)
   - **Supported account types**: *Accounts in this organizational directory only* (Single tenant)
   - **Redirect URI**: leave blank
3. Click **Register**

### 1.2 Copy your IDs

On the **Overview** page after registration:

| Field in Azure | Variable in `secrets.toml` |
|---|---|
| Application (client) ID | `GRAPH_CLIENT_ID` |
| Directory (tenant) ID | `GRAPH_TENANT_ID` |

### 1.3 Grant API permissions

1. Left sidebar → **API permissions** → **Add a permission**
2. Choose **Microsoft Graph** → **Application permissions**
3. Search for `Sites.ReadWrite.All` and check it
4. Click **Add permissions**
5. Click **Grant admin consent for [your org]** — this button requires a Global Admin account
6. Status should show a green checkmark

### 1.4 Create a client secret

1. Left sidebar → **Certificates & secrets** → **New client secret**
2. Description: `tidepool-logger`, Expiry: 24 months (recommended)
3. Click **Add**
4. **Copy the Value column immediately** — Azure will never show it again
5. Paste it as `GRAPH_CLIENT_SECRET` in `secrets.toml`

---

## 2 — Excel File Setup

Create **two** separate Excel files in your SharePoint document library (e.g. in *Documents* or a dedicated *Tidepool* folder).

### 2.1 GiftingLog.xlsx

1. Open or create the file in SharePoint → **Edit in Excel for the web**
2. In Sheet1, click any cell, then **Insert → Table** (check *My table has headers*)
3. **Table Design** (top ribbon) → change **Table Name** to exactly: `GiftingLog`
4. Set these column headers in row 1, in this exact order:

```
Timestamp | Recipient | Bags | Venue | Date | LoggedBy | Notes | Posted | PostLink | ContentType
```

### 2.2 EventLog.xlsx

Same process — create a table named exactly `EventLog` with headers in this order:

```
Timestamp | Venue | VenueType | EventDate | BagsAllocated | LoggedBy | Sampled | Sold | Leads | Followups | Notes | Status
```

> **Important**: Table names are case-sensitive. The app sends `GiftingLog` and `EventLog` verbatim to the Graph API.

---

## 3 — Find SharePoint Site ID and File IDs

Use **[Microsoft Graph Explorer](https://developer.microsoft.com/en-us/graph/graph-explorer)** — sign in with your Microsoft 365 account.

### 3.1 SharePoint Site ID

Run:
```
GET https://graph.microsoft.com/v1.0/sites?search=*
```

Or if you know your SharePoint hostname and site path:
```
GET https://graph.microsoft.com/v1.0/sites/yourcompany.sharepoint.com:/sites/YourSiteName
```

Copy the `"id"` field from the response → `SHAREPOINT_SITE_ID` in `secrets.toml`.

> The site ID looks like: `yourcompany.sharepoint.com,xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx,xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

### 3.2 File IDs (for each Excel file)

List files in the site drive:
```
GET https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/drive/root/children
```

If your files are in a subfolder (e.g. `Documents/Tidepool`):
```
GET https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/drive/root:/Documents/Tidepool:/children
```

Find `GiftingLog.xlsx` and `EventLog.xlsx` in the response array. Copy each file's `"id"` field:
- GiftingLog.xlsx `id` → `GIFTING_FILE_ID`
- EventLog.xlsx `id` → `EVENTS_FILE_ID`

---

## 4 — Local Development

### 4.1 Install dependencies

```bash
cd tidepool-logger
pip install -r requirements.txt
```

### 4.2 Configure secrets

Edit `.streamlit/secrets.toml` — replace every placeholder with your real values:

```toml
GRAPH_TENANT_ID     = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
GRAPH_CLIENT_ID     = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
GRAPH_CLIENT_SECRET = "your~secret~value~here"
SHAREPOINT_SITE_ID  = "yourcompany.sharepoint.com,xxxx...,xxxx..."
GIFTING_FILE_ID     = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
EVENTS_FILE_ID      = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
ANTHROPIC_API_KEY   = "sk-ant-..."
APP_PASSWORD        = "tidepool2025"
```

### 4.3 Run the app

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501). Password is `tidepool2025` (or whatever you set in `APP_PASSWORD`).

---

## 5 — Streamlit Cloud Deployment

### 5.1 Push to GitHub

Make sure `.streamlit/secrets.toml` stays out of git (the `.gitignore` already excludes it):

```bash
git init
git add .
git commit -m "Initial TIDEPOOL Logger"
git remote add origin https://github.com/your-org/tidepool-logger.git
git push -u origin main
```

### 5.2 Deploy on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
2. Connect your GitHub account → choose the `tidepool-logger` repo
3. Set **Main file path**: `app.py`
4. Click **Deploy**

### 5.3 Add secrets in Streamlit Cloud

1. Once deployed, click **⋮ (three dots)** → **Settings** → **Secrets**
2. Paste the full contents of your `secrets.toml` (with real values, not placeholders)
3. Click **Save** — the app will restart automatically

Your app is now live at `https://<your-app-name>.streamlit.app`.

---

## App Usage

| Feature | How it works |
|---|---|
| Password gate | Blocks access until the correct `APP_PASSWORD` is entered |
| **Gifting Log** | Log product gifting. Paste a natural-language description and hit *Parse with AI* to pre-fill fields automatically |
| **Event Wrap-Up → Pre-Event** | Log an upcoming event before it happens; sets Status = `Pre-logged` |
| **Event Wrap-Up → Post-Event** | Select a pre-logged event, fill in results, submit to mark Status = `Complete` |

### Data written to SharePoint

**GiftingLog** columns:
`Timestamp | Recipient | Bags | Venue | Date | LoggedBy | Notes | Posted | PostLink | ContentType`

**EventLog** columns:
`Timestamp | Venue | VenueType | EventDate | BagsAllocated | LoggedBy | Sampled | Sold | Leads | Followups | Notes | Status`

---

## Creator Applications Setup

### 2.3 TIDEPOOL_Creator_Applications.xlsx

Create a **third** Excel file in the same SharePoint document library as `GiftingLog.xlsx` and `EventLog.xlsx`.

1. In SharePoint, click **New → Excel workbook** and name it `TIDEPOOL_Creator_Applications`
2. Open it → **Edit in Excel for the web**
3. In Sheet1, click any cell → **Insert → Table** (check *My table has headers*)
4. **Table Design** → change **Table Name** to exactly: `CreatorApplications`
5. Set these column headers in row 1, in this exact order:

```
Timestamp | CampaignName | Platform | Name | InstagramFollowers | TikTokFollowers | ApplicationResponse | Status | Score | Reasoning | ContentAngle | WholesaleFlag | LoggedBy
```

> **Important**: Table name and column headers are case-sensitive. The app sends `CreatorApplications` verbatim to the Graph API.

### Find the File ID

In [Microsoft Graph Explorer](https://developer.microsoft.com/en-us/graph/graph-explorer), list your SharePoint drive files:

```
GET https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/drive/root/children
```

(Adjust the path if your file is in a subfolder, e.g. `.../drive/root:/Documents/Tidepool:/children`)

Find `TIDEPOOL_Creator_Applications.xlsx` in the response and copy its `"id"` field.

Paste it into `.streamlit/secrets.toml`:

```toml
CREATOR_FILE_ID = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

Also add it to the **Secrets** panel in Streamlit Cloud when deploying.

---

## Troubleshooting

| Error | Likely cause |
|---|---|
| `Auth error 401` | Client secret wrong or expired; regenerate in Azure |
| `Auth error 403` | Admin consent not granted for `Sites.ReadWrite.All` |
| `Append error 404` | Wrong `SHAREPOINT_SITE_ID` or `GIFTING_FILE_ID` / `EVENTS_FILE_ID` |
| `Append error 400` on table rows | Table name mismatch — must be exactly `GiftingLog` or `EventLog` |
| AI parse fails | Invalid or expired `ANTHROPIC_API_KEY` |
| No pre-logged events shown | EventLog table is empty or no rows have `Status = Pre-logged` |
| Creator Applications tab errors | `CREATOR_FILE_ID` missing or wrong, or `CreatorApplications` table not created |
