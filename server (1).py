from flask import Flask, request, jsonify, send_from_directory
import sqlite3, json, os, time

app = Flask(__name__, static_folder='.')
DB = os.path.join(os.environ.get('RAILWAY_VOLUME_MOUNT_PATH', '.'), 'lexhub.db')

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS cases (
            id TEXT PRIMARY KEY, case_number TEXT, title TEXT, client TEXT,
            opposing TEXT, status TEXT DEFAULT 'Active', court TEXT,
            type TEXT, next_hearing TEXT, assignee TEXT, value TEXT,
            notes TEXT, timeline TEXT DEFAULT '[]',
            created_at REAL, updated_at REAL
        );
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS attorneys (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE IF NOT EXISTS courts (id INTEGER PRIMARY KEY, name TEXT, display_order INTEGER DEFAULT 0);
    ''')
    existing = conn.execute('SELECT COUNT(*) FROM courts').fetchone()[0]
    if existing == 0:
        defaults = [
            'Dubai Court of First Instance','Dubai Court of Appeal','Dubai Court of Cassation',
            'DIFC Court','Execution Court','Personal Status Court','Labour Court',
            'ADGM Court','Arbitration (DIAC)','Arbitration (ICC)',
        ]
        for i, name in enumerate(defaults):
            conn.execute('INSERT INTO courts (name, display_order) VALUES (?,?)', (name, i))
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/cases', methods=['GET'])
def get_cases():
    conn = get_db()
    rows = conn.execute('SELECT * FROM cases ORDER BY created_at DESC').fetchall()
    conn.close()
    result = []
    for r in rows:
        c = dict(r)
        c['timeline'] = json.loads(c['timeline'] or '[]')
        result.append(c)
    return jsonify(result)

@app.route('/api/cases', methods=['POST'])
def add_case():
    d = request.json
    import uuid
    cid = str(uuid.uuid4())[:8]
    now = time.time()
    tl = json.dumps(d.get('timeline', []))
    conn = get_db()
    conn.execute('INSERT INTO cases VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (cid,d.get('case_number'),d.get('title'),d.get('client'),d.get('opposing'),
         d.get('status','Active'),d.get('court'),d.get('type'),d.get('next_hearing'),
         d.get('assignee'),d.get('value'),d.get('notes'),tl,now,now))
    conn.commit()
    row = dict(conn.execute('SELECT * FROM cases WHERE id=?',(cid,)).fetchone())
    conn.close()
    row['timeline'] = json.loads(row['timeline'])
    return jsonify(row)

@app.route('/api/cases/<cid>', methods=['PUT'])
def update_case(cid):
    d = request.json
    conn = get_db()
    row = conn.execute('SELECT * FROM cases WHERE id=?',(cid,)).fetchone()
    if not row: conn.close(); return jsonify({'error':'not found'}),404
    tl = json.loads(row['timeline'] or '[]')
    if d.get('new_timeline_entry'):
        from datetime import date
        tl.append({'date': str(date.today()), 'text': d['new_timeline_entry']})
    conn.execute('''UPDATE cases SET case_number=?,title=?,client=?,opposing=?,status=?,
        court=?,type=?,next_hearing=?,assignee=?,value=?,notes=?,timeline=?,updated_at=? WHERE id=?''',
        (d.get('case_number'),d.get('title'),d.get('client'),d.get('opposing'),d.get('status'),
         d.get('court'),d.get('type'),d.get('next_hearing'),d.get('assignee'),d.get('value'),
         d.get('notes'),json.dumps(tl),time.time(),cid))
    conn.commit()
    row = dict(conn.execute('SELECT * FROM cases WHERE id=?',(cid,)).fetchone())
    conn.close()
    row['timeline'] = json.loads(row['timeline'])
    return jsonify(row)

@app.route('/api/cases/<cid>', methods=['DELETE'])
def delete_case(cid):
    conn = get_db()
    conn.execute('DELETE FROM cases WHERE id=?',(cid,))
    conn.commit(); conn.close()
    return jsonify({'success':True})

@app.route('/api/settings', methods=['GET'])
def get_settings():
    conn = get_db()
    rows = conn.execute('SELECT key,value FROM settings').fetchall()
    conn.close()
    return jsonify({r['key']:r['value'] for r in rows})

@app.route('/api/settings', methods=['POST'])
def save_settings():
    d = request.json
    conn = get_db()
    for k,v in d.items():
        conn.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',(k,v))
    conn.commit(); conn.close()
    return jsonify({'success':True})

@app.route('/api/attorneys', methods=['GET'])
def get_attorneys():
    conn = get_db()
    rows = conn.execute('SELECT name FROM attorneys ORDER BY id').fetchall()
    conn.close()
    return jsonify([r['name'] for r in rows])

@app.route('/api/attorneys', methods=['POST'])
def save_attorneys():
    names = request.json.get('names',[])
    conn = get_db()
    conn.execute('DELETE FROM attorneys')
    for n in names:
        conn.execute('INSERT INTO attorneys (name) VALUES (?)',(n,))
    conn.commit(); conn.close()
    return jsonify({'success':True})

@app.route('/api/courts', methods=['GET'])
def get_courts():
    conn = get_db()
    rows = conn.execute('SELECT name FROM courts ORDER BY display_order, id').fetchall()
    conn.close()
    return jsonify([r['name'] for r in rows])

@app.route('/api/courts', methods=['POST'])
def save_courts():
    names = request.json.get('names', [])
    conn = get_db()
    conn.execute('DELETE FROM courts')
    for i, name in enumerate(names):
        conn.execute('INSERT INTO courts (name, display_order) VALUES (?,?)', (name, i))
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/export')
def export_data():
    conn = get_db()
    cases = [dict(r) for r in conn.execute('SELECT * FROM cases').fetchall()]
    for c in cases: c['timeline'] = json.loads(c['timeline'] or '[]')
    attorneys = [r['name'] for r in conn.execute('SELECT name FROM attorneys').fetchall()]
    settings = {r['key']:r['value'] for r in conn.execute('SELECT key,value FROM settings').fetchall()}
    courts = [r['name'] for r in conn.execute('SELECT name FROM courts ORDER BY display_order').fetchall()]
    conn.close()
    from flask import Response
    return Response(json.dumps({'cases':cases,'attorneys':attorneys,'settings':settings,'courts':courts},indent=2),
        mimetype='application/json',
        headers={'Content-Disposition':'attachment;filename=lexhub-backup.json'})

@app.route('/api/import', methods=['POST'])
def import_data():
    d = request.json
    conn = get_db()
    imported = 0
    for c in d.get('cases',[]):
        try:
            conn.execute('INSERT OR REPLACE INTO cases VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (c.get('id'),c.get('case_number'),c.get('title'),c.get('client'),c.get('opposing'),
                 c.get('status','Active'),c.get('court'),c.get('type'),c.get('next_hearing'),
                 c.get('assignee'),c.get('value'),c.get('notes'),
                 json.dumps(c.get('timeline',[])),c.get('created_at',time.time()),c.get('updated_at',time.time())))
            imported += 1
        except: pass
    conn.commit(); conn.close()
    return jsonify({'imported':imported})

if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get('PORT',5000)))
