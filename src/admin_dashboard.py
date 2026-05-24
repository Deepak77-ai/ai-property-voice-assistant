
from flask import Flask, render_template_string
from src.data.lead_store import load_leads
from src.data.conversation_store import get_all_conversations

app = Flask(__name__)



DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Real Estate AI — Admin</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Fraunces:ital,wght@0,300;0,600;1,300&display=swap');

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg:       #0f0f0f;
      --surface:  #181818;
      --border:   #2a2a2a;
      --text:     #e8e2d9;
      --muted:    #6b6560;
      --hot:      #e05c3a;
      --warm:     #d4943a;
      --cold:     #4a90c4;
      --accent:   #c9b99a;
      --mono:     'DM Mono', monospace;
      --serif:    'Fraunces', Georgia, serif;
    }

    body {
      background: var(--bg);
      color: var(--text);
      font-family: var(--mono);
      font-size: 13px;
      line-height: 1.6;
      min-height: 100vh;
      padding: 48px 40px;
    }

    /* ── Header ── */
    header {
      border-bottom: 1px solid var(--border);
      padding-bottom: 24px;
      margin-bottom: 48px;
      display: flex;
      align-items: baseline;
      gap: 16px;
    }
    header h1 {
      font-family: var(--serif);
      font-weight: 300;
      font-size: 28px;
      letter-spacing: -0.5px;
      color: var(--accent);
    }
    header span {
      color: var(--muted);
      font-size: 11px;
      letter-spacing: 2px;
      text-transform: uppercase;
    }

    /* ── Section titles ── */
    h2 {
      font-family: var(--serif);
      font-weight: 300;
      font-size: 18px;
      color: var(--accent);
      margin-bottom: 20px;
    }

    section { margin-bottom: 56px; }

    /* ── Stat cards ── */
    .stats {
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
      margin-bottom: 48px;
    }
    .stat-card {
      background: var(--surface);
      border: 1px solid var(--border);
      padding: 20px 28px;
      min-width: 130px;
      flex: 1;
    }
    .stat-card .label {
      font-size: 10px;
      letter-spacing: 2px;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 8px;
    }
    .stat-card .value {
      font-family: var(--serif);
      font-size: 36px;
      font-weight: 600;
      line-height: 1;
    }
    .stat-card.hot  .value { color: var(--hot); }
    .stat-card.warm .value { color: var(--warm); }
    .stat-card.cold .value { color: var(--cold); }
    .stat-card.total .value { color: var(--text); }

    /* ── Table ── */
    .table-wrap { overflow-x: auto; }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }
    thead tr {
      border-bottom: 1px solid var(--border);
    }
    thead th {
      text-align: left;
      padding: 10px 14px;
      font-size: 10px;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      color: var(--muted);
      font-weight: 500;
    }
    tbody tr {
      border-bottom: 1px solid var(--border);
      transition: background 0.15s;
    }
    tbody tr:hover { background: var(--surface); }
    tbody td {
      padding: 12px 14px;
      color: var(--text);
    }

    /* Quality badge */
    .badge {
      display: inline-block;
      padding: 2px 10px;
      font-size: 10px;
      letter-spacing: 1px;
      text-transform: uppercase;
      font-weight: 500;
      border: 1px solid currentColor;
    }
    .badge.Hot  { color: var(--hot); }
    .badge.Warm { color: var(--warm); }
    .badge.Cold { color: var(--cold); }

    /* Score bar */
    .score-wrap { display: flex; align-items: center; gap: 8px; }
    .score-bar-bg {
      width: 60px; height: 4px;
      background: var(--border);
      position: relative;
    }
    .score-bar-fill {
      height: 100%;
      background: var(--accent);
    }

    /* ── Conversations ── */
    .conversation {
      background: var(--surface);
      border: 1px solid var(--border);
      padding: 20px 24px;
      margin-bottom: 16px;
    }
    .conv-id {
      font-size: 10px;
      letter-spacing: 2px;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 14px;
      padding-bottom: 10px;
      border-bottom: 1px solid var(--border);
    }
    .message { display: flex; gap: 12px; margin-bottom: 10px; }
    .role-tag {
      font-size: 10px;
      letter-spacing: 1px;
      text-transform: uppercase;
      padding-top: 2px;
      min-width: 70px;
      color: var(--muted);
    }
    .role-tag.user      { color: var(--accent); }
    .role-tag.assistant { color: var(--cold); }
    .msg-text { color: var(--text); }
    .msg-time { color: var(--muted); font-size: 11px; margin-top: 2px; }

    /* ── Empty state ── */
    .empty {
      color: var(--muted);
      font-style: italic;
      padding: 24px 0;
    }
  </style>
</head>
<body>

  <header>
    <h1>Real Estate AI</h1>
    <span>Admin Dashboard</span>
  </header>

  <!-- ── Stats ── -->
  <div class="stats">
    <div class="stat-card total">
      <div class="label">Total Leads</div>
      <div class="value">{{ total }}</div>
    </div>
    <div class="stat-card hot">
      <div class="label">Hot</div>
      <div class="value">{{ hot }}</div>
    </div>
    <div class="stat-card warm">
      <div class="label">Warm</div>
      <div class="value">{{ warm }}</div>
    </div>
    <div class="stat-card cold">
      <div class="label">Cold</div>
      <div class="value">{{ cold }}</div>
    </div>
  </div>

  <!-- ── Leads Table ── -->
  <section>
    <h2>Leads</h2>
    {% if leads %}
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Name</th>
            <th>Phone</th>
            <th>City</th>
            <th>Budget</th>
            <th>Type</th>
            <th>Intent</th>
            <th>Score</th>
            <th>Quality</th>
          </tr>
        </thead>
        <tbody>
          {% for l in leads %}
          <tr>
            <td>{{ l.created_at }}</td>
            <td>{{ l.name or "—" }}</td>
            <td>{{ l.phone or "—" }}</td>
            <td>{{ l.city or "—" }}</td>
            <td>{{ l.budget or "—" }}</td>
            <td>{{ l.property_type or "—" }}</td>
            <td>{{ l.intent or "—" }}</td>
            <td>
              <div class="score-wrap">
                {{ l.lead_score }}
                <div class="score-bar-bg">
                  <div class="score-bar-fill" style="width: {{ l.lead_score }}%;"></div>
                </div>
              </div>
            </td>
            <td><span class="badge {{ l.lead_quality }}">{{ l.lead_quality }}</span></td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}
      <p class="empty">No leads saved yet.</p>
    {% endif %}
  </section>

  <!-- ── Conversations ── -->
  <section>
    <h2>Conversations</h2>
    {% if conversations %}
      {% for cid, msgs in conversations.items() %}
      <div class="conversation">
        <div class="conv-id">{{ cid }}</div>
        {% for m in msgs %}
        <div class="message">
          <div class="role-tag {{ m.role }}">{{ m.role }}</div>
          <div>
            <div class="msg-text">{{ m.message }}</div>
            <div class="msg-time">{{ m.time }}</div>
          </div>
        </div>
        {% endfor %}
      </div>
      {% endfor %}
    {% else %}
      <p class="empty">No conversations recorded yet.</p>
    {% endif %}
  </section>

</body>
</html>
"""



@app.route("/")
def dashboard():
    
    leads         = load_leads()
    conversations = get_all_conversations()

    total = len(leads)
    hot   = sum(1 for l in leads if l["lead_quality"] == "Hot")
    warm  = sum(1 for l in leads if l["lead_quality"] == "Warm")
    cold  = sum(1 for l in leads if l["lead_quality"] == "Cold")

    return render_template_string(
        DASHBOARD_HTML,
        leads=leads,
        conversations=conversations,
        total=total,
        hot=hot,
        warm=warm,
        cold=cold,
    )




if __name__ == "__main__":
    
    app.run(port=5001, debug=True)