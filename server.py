"""
LexHub Pro — Backend Server
Run with: python server.py
Then open: http://localhost:5000
"""

from flask import Flask, request, jsonify, send_from_directory
import sqlite3, os, json
from datetime import datetime

import os as _os
app = Flask(__name__, static_folder=_os.path.dirname(_os.path.abspath(__file__)))
DATA_DIR = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH', os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(DATA_DIR, 'lexhub.db')

# ── Database setup ──────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS cases (
                id          TEXT PRIMARY KEY,
                case_number TEXT,
                title       TEXT NOT NULL,
                client      TEXT,
                opposing    TEXT,
                status      TEXT DEFAULT 'Active',
                court       TEXT,
                type        TEXT,
                next_hearing TEXT,
                assignee    TEXT,
                value       TEXT,
                notes       TEXT,
                created_at  INTEGER,
                updated_at  INTEGER
            );

            CREATE TABLE IF NOT EXISTS timeline (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id  TEXT NOT NULL,
                date     TEXT NOT NULL,
                text     TEXT NOT NULL,
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS attorneys (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                name  TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        # Seed attorneys
        attorneys = ['Sudheer Devarajan', 'Attorney 2', 'Attorney 3', 'Attorney 4']
        for a in attorneys:
            db.execute("INSERT OR IGNORE INTO attorneys (name) VALUES (?)", (a,))
        # Seed firm name
        db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('firm_name', 'Your Law Firm')")
        db.commit()
        # Seed real cases if empty
        count = db.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        if count == 0:
            seed_cases(db)

def seed_cases(db):
    from datetime import date, timedelta
    today = date.today()
    def fdate(days): return (today + timedelta(days=days)).isoformat()

    cases = [
        {
            'id': 'case_001',
            'case_number': 'OMAN/ARB/2026/001',
            'title': 'Rashid Al-Mughaizwi Trad. & Cont. Co. v. NOMAC Maintenance Energy Services',
            'client': 'Rashid Salim Humaid Al-Mughaizwi Trading & Contracting Co.',
            'opposing': 'NOMAC Maintenance Energy Services (NMES)',
            'status': 'Active',
            'court': 'Dubai Court of First Instance',
            'type': 'Commercial',
            'next_hearing': fdate(21),
            'assignee': 'Sudheer Devarajan',
            'value': 'OMR 56,813',
            'notes': 'Unpaid invoice claim for manpower services rendered at Sohar 3 GT & GTG 11 outage works in Oman (Feb–Apr 2025). Client performed services under Service Agreement dated 30 May 2023 and LPO No. 8300032314. Invoice No. RSHM/INV/NMES/43/2025 submitted May 2025. Respondent requested revised invoice with updated bank details on 5 Aug 2025 — revised invoice submitted same day. On 5 Feb 2026, Respondent issued Notice of Rescission (signed by EVP Harald Schmit) alleging bribery and corruption — all allegations categorically denied. Respondent incorrectly referenced PO No. 8300034904 which was already fully paid. Affirmation of contract argued through Respondent conduct.',
            'created_at': 1700000000,
            'updated_at': 1700000000,
            'timeline': [
                ('2023-05-30', 'Service Agreement executed between client and NMES'),
                ('2025-02-01', 'Client mobilised manpower for Sohar 3 GT & GTG 11 outage under LPO No. 8300032314'),
                ('2025-05-10', 'Tax Invoice No. RSHM/INV/NMES/43/2025 submitted — OMR 56,813.794'),
                ('2025-08-05', 'NMES requested revised invoice with updated bank account details. Revised invoice submitted same day.'),
                ('2026-02-05', 'NMES issued Notice of Rescission alleging bribery and corruption — signed by EVP Harald Schmit.'),
                ('2026-03-06', 'Statement of Case prepared. Client categorically denies all allegations.'),
            ]
        },
        {
            'id': 'case_002',
            'case_number': 'UAE/LAB/2026/002',
            'title': 'Amol Vishnu Shinde — Suspension & Disciplinary Defence',
            'client': 'Amol Vishnu Shinde',
            'opposing': 'RNA Resource Group Ltd / Splash (Landmark Group)',
            'status': 'Active',
            'court': 'Labour Court',
            'type': 'Labour',
            'next_hearing': fdate(14),
            'assignee': 'Sudheer Devarajan',
            'value': 'AED 18,400/month',
            'notes': 'Client is Buying Manager at Splash (Landmark Group), employed since Jan 2017, salary AED 18,400/month. Suspended 20 Jan 2026. Allegations: (1) Commission via spousal salary; (2) Leaking confidential info to Apparel Group; (3) Supplier favouritism toward Icarus Fashion; (4) Money laundering re Indian property funds; (5) Bank forgery by wife. Investigation ongoing. Client denies all allegations.',
            'created_at': 1700000001,
            'updated_at': 1700000001,
            'timeline': [
                ('2017-01-30', 'Client joined Splash (Landmark Group) as Assistant Buyer'),
                ('2017-09-05', 'Probation completed. Confirmed as regular employee.'),
                ('2021-09-15', 'Mrs. Tejasvi commenced employment at RN Enterprise Bangladesh — AED 8,000/month'),
                ('2026-01-20', 'Client suspended from duties. Disciplinary Investigation Meeting held same day.'),
                ('2026-03-06', 'Summary of facts prepared. Defence strategy under preparation.'),
            ]
        },
        {
            'id': 'case_003',
            'case_number': 'DIFC/2026/003',
            'title': 'Sidorov v. Inovexa Holding Co. & Jogi De Silva',
            'client': 'Jogi De Silva (Respondent 2)',
            'opposing': 'Vyacheslav Sidorov',
            'status': 'Active',
            'court': 'DIFC Court',
            'type': 'Commercial',
            'next_hearing': fdate(10),
            'assignee': 'Sudheer Devarajan',
            'value': '',
            'notes': 'Claimant Sidorov alleges unlawful share transfer of Inovexa Holding shares to De Silva on 22 Apr 2025, fraud, and forgery. Expert report strongly in client favour: Inovexa beneficial owner was always Yevgeny Gorokhov — Sidorov was nominal only; Meydan Free Zone confirmed transfer was consensual; no damages established; claimant own representatives acknowledged signature was abbreviated variant. Sole live issue: forgery allegation — significantly weakened by claimant own concession.',
            'created_at': 1700000002,
            'updated_at': 1700000002,
            'timeline': [
                ('2024-08-07', 'Consultancy agreement between White Square Company and Gorokhov — Inovexa to be set up with Sidorov as nominal owner'),
                ('2024-08-23', 'Inovexa Holding Company incorporated at Meydan Free Zone. Sidorov listed as nominal owner/manager only.'),
                ('2025-04-22', 'Share transfer executed — De Silva replaced Sidorov as nominal owner per Gorokhov direction.'),
                ('2026-02-06', 'Claimant representatives acknowledged signature was abbreviated variant used from Nov 2024.'),
                ('2026-02-19', 'Meydan Free Zone confirmed to expert that transfer was carried out with claimant knowledge and consent.'),
                ('2026-02-25', 'Claimant raised forgery allegation late in proceedings.'),
                ('2026-03-06', 'Expert report note prepared. Findings almost entirely in client favour.'),
            ]
        }
    ]

    for c in cases:
        timeline = c.pop('timeline')
        db.execute("""INSERT INTO cases (id,case_number,title,client,opposing,status,court,type,
                      next_hearing,assignee,value,notes,created_at,updated_at)
                      VALUES (:id,:case_number,:title,:client,:opposing,:status,:court,:type,
                      :next_hearing,:assignee,:value,:notes,:created_at,:updated_at)""", c)
        for date, text in timeline:
            db.execute("INSERT INTO timeline (case_id,date,text) VALUES (?,?,?)", (c['id'], date, text))
    db.commit()

# ── Helpers ─────────────────────────────────────────────────
def case_to_dict(row, db):
    c = dict(row)
    rows = db.execute("SELECT date, text FROM timeline WHERE case_id=? ORDER BY date ASC", (c['id'],)).fetchall()
    c['timeline'] = [{'date': r['date'], 'text': r['text']} for r in rows]
    return c

import uuid
def new_id():
    return str(uuid.uuid4())[:12]

# ── API Routes ───────────────────────────────────────────────
@app.route('/api/cases', methods=['GET'])
def get_cases():
    with get_db() as db:
        rows = db.execute("SELECT * FROM cases ORDER BY created_at DESC").fetchall()
        return jsonify([case_to_dict(r, db) for r in rows])

@app.route('/api/cases', methods=['POST'])
def create_case():
    data = request.json
    cid = new_id()
    now = int(datetime.now().timestamp())
    with get_db() as db:
        db.execute("""INSERT INTO cases (id,case_number,title,client,opposing,status,court,type,
                      next_hearing,assignee,value,notes,created_at,updated_at)
                      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (cid, data.get('case_number',''), data.get('title',''), data.get('client',''),
                    data.get('opposing',''), data.get('status','Active'), data.get('court',''),
                    data.get('type',''), data.get('next_hearing',''), data.get('assignee',''),
                    data.get('value',''), data.get('notes',''), now, now))
        for t in data.get('timeline', []):
            db.execute("INSERT INTO timeline (case_id,date,text) VALUES (?,?,?)", (cid, t['date'], t['text']))
        db.commit()
        row = db.execute("SELECT * FROM cases WHERE id=?", (cid,)).fetchone()
        return jsonify(case_to_dict(row, db))

@app.route('/api/cases/<cid>', methods=['PUT'])
def update_case(cid):
    data = request.json
    now = int(datetime.now().timestamp())
    with get_db() as db:
        db.execute("""UPDATE cases SET case_number=?,title=?,client=?,opposing=?,status=?,court=?,
                      type=?,next_hearing=?,assignee=?,value=?,notes=?,updated_at=? WHERE id=?""",
                   (data.get('case_number',''), data.get('title',''), data.get('client',''),
                    data.get('opposing',''), data.get('status','Active'), data.get('court',''),
                    data.get('type',''), data.get('next_hearing',''), data.get('assignee',''),
                    data.get('value',''), data.get('notes',''), now, cid))
        # Add new timeline entry if provided
        new_entry = data.get('new_timeline_entry','').strip()
        if new_entry:
            today = datetime.now().strftime('%Y-%m-%d')
            db.execute("INSERT INTO timeline (case_id,date,text) VALUES (?,?,?)", (cid, today, new_entry))
        db.commit()
        row = db.execute("SELECT * FROM cases WHERE id=?", (cid,)).fetchone()
        return jsonify(case_to_dict(row, db))

@app.route('/api/cases/<cid>', methods=['DELETE'])
def delete_case(cid):
    with get_db() as db:
        db.execute("DELETE FROM timeline WHERE case_id=?", (cid,))
        db.execute("DELETE FROM cases WHERE id=?", (cid,))
        db.commit()
    return jsonify({'success': True})

@app.route('/api/attorneys', methods=['GET'])
def get_attorneys():
    with get_db() as db:
        rows = db.execute("SELECT name FROM attorneys ORDER BY id").fetchall()
        return jsonify([r['name'] for r in rows])

@app.route('/api/attorneys', methods=['POST'])
def save_attorneys():
    names = request.json.get('names', [])
    with get_db() as db:
        db.execute("DELETE FROM attorneys")
        for name in names:
            if name.strip():
                db.execute("INSERT INTO attorneys (name) VALUES (?)", (name.strip(),))
        db.commit()
    return jsonify({'success': True})

@app.route('/api/settings', methods=['GET'])
def get_settings():
    with get_db() as db:
        rows = db.execute("SELECT key, value FROM settings").fetchall()
        return jsonify({r['key']: r['value'] for r in rows})

@app.route('/api/settings', methods=['POST'])
def save_settings():
    data = request.json
    with get_db() as db:
        for key, value in data.items():
            db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
        db.commit()
    return jsonify({'success': True})

@app.route('/api/export', methods=['GET'])
def export_db():
    with get_db() as db:
        cases = db.execute("SELECT * FROM cases ORDER BY created_at DESC").fetchall()
        result = []
        for c in cases:
            cd = case_to_dict(c, db)
            result.append(cd)
    from flask import Response
    return Response(
        json.dumps(result, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename=lexhub-backup-{datetime.now().strftime("%Y%m%d")}.json'}
    )

@app.route('/api/import', methods=['POST'])
def import_db():
    data = request.json
    now = int(datetime.now().timestamp())
    with get_db() as db:
        for c in data:
            timeline = c.pop('timeline', [])
            exists = db.execute("SELECT id FROM cases WHERE id=?", (c['id'],)).fetchone()
            if exists:
                db.execute("""UPDATE cases SET case_number=?,title=?,client=?,opposing=?,status=?,
                              court=?,type=?,next_hearing=?,assignee=?,value=?,notes=?,updated_at=? WHERE id=?""",
                           (c.get('case_number',''), c.get('title',''), c.get('client',''),
                            c.get('opposing',''), c.get('status','Active'), c.get('court',''),
                            c.get('type',''), c.get('next_hearing',''), c.get('assignee',''),
                            c.get('value',''), c.get('notes',''), now, c['id']))
            else:
                db.execute("""INSERT OR IGNORE INTO cases (id,case_number,title,client,opposing,status,
                              court,type,next_hearing,assignee,value,notes,created_at,updated_at)
                              VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                           (c['id'], c.get('case_number',''), c.get('title',''), c.get('client',''),
                            c.get('opposing',''), c.get('status','Active'), c.get('court',''),
                            c.get('type',''), c.get('next_hearing',''), c.get('assignee',''),
                            c.get('value',''), c.get('notes',''), c.get('created_at', now), now))
                for t in timeline:
                    db.execute("INSERT INTO timeline (case_id,date,text) VALUES (?,?,?)",
                               (c['id'], t['date'], t['text']))
        db.commit()
    return jsonify({'success': True, 'imported': len(data)})

# ── Serve frontend ───────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory(_os.path.dirname(_os.path.abspath(__file__)), 'index.html')

if __name__ == '__main__':
    init_db()
    print("\n" + "="*50)
    print("  LexHub Pro is running!")
    print("  Open your browser at: http://localhost:5000")
    print("  Your database is saved at:", DB_PATH)
    print("  Press Ctrl+C to stop the server")
    print("="*50 + "\n")
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
