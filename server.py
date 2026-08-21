from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
import sqlite3, json, os, subprocess, tempfile, shutil, sys

ROOT=os.path.dirname(os.path.abspath(__file__))
DB=os.path.join(ROOT,'data','ikami.sqlite3')
os.makedirs(os.path.dirname(DB),exist_ok=True)

def db():
    c=sqlite3.connect(DB)
    c.row_factory=sqlite3.Row
    c.execute('''CREATE TABLE IF NOT EXISTS counters(code TEXT PRIMARY KEY, value INTEGER NOT NULL DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY AUTOINCREMENT, nomor TEXT NOT NULL, hal TEXT, kepada TEXT, tanggal TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    c.commit(); return c

def json_out(h, code, obj):
    b=json.dumps(obj,ensure_ascii=False).encode(); h.send_response(code); h.send_header('Content-Type','application/json; charset=utf-8'); h.send_header('Content-Length',str(len(b))); h.end_headers(); h.wfile.write(b)

class Handler(SimpleHTTPRequestHandler):
    def translate_path(self,path):
        path=urlparse(path).path
        if path=='/': path='/index.html'
        return os.path.join(ROOT,path.lstrip('/').replace('/',os.sep))

    def end_headers(self):
        # Jangan gunakan halaman HTML lama dari cache browser.
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()
    def do_GET(self):
        p=urlparse(self.path).path
        c=db()
        try:
            if p=='/api/counters':
                rows=c.execute('SELECT code,value FROM counters').fetchall(); return json_out(self,200,{r['code']:r['value'] for r in rows})
            if p=='/api/history':
                rows=c.execute('SELECT id,nomor,hal,kepada,tanggal,created_at FROM history ORDER BY id DESC LIMIT 100').fetchall(); return json_out(self,200,[dict(r) for r in rows])
        finally: c.close()
        return super().do_GET()
    def do_POST(self):
        p = urlparse(self.path).path
        n = int(self.headers.get('Content-Length', '0'))

        # PDF endpoint menerima BODY BINARY DOCX, bukan JSON.
        # Jangan membaca body sebagai JSON terlebih dahulu karena itu akan
        # menghabiskan stream request dan membuat file DOCX yang dikirim ke
        # converter menjadi kosong.
        if p == '/api/convert-pdf':
            raw = self.rfile.read(n)
            if not raw:
                return json_out(self, 400, {'error': 'File DOCX kosong atau tidak terkirim.'})

            with tempfile.TemporaryDirectory() as td:
                src = os.path.join(td, 'surat.docx')
                pdf = os.path.join(td, 'surat.pdf')
                with open(src, 'wb') as f:
                    f.write(raw)

                # PRIORITAS 1: Microsoft Word di Windows.
                # Word adalah sumber layout yang paling dekat dengan DOCX
                # master karena menggunakan engine Word sendiri.
                word_ok = False
                word_error = ''
                if os.name == 'nt':
                    ps = os.path.join(ROOT, 'word_to_pdf.ps1')
                    powershell = shutil.which('powershell.exe') or shutil.which('powershell')
                    if powershell and os.path.exists(ps):
                        try:
                            r = subprocess.run(
                                [powershell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ps, src, pdf],
                                capture_output=True, text=True, timeout=120
                            )
                            word_ok = (r.returncode == 0 and os.path.isfile(pdf) and os.path.getsize(pdf) > 0)
                            if not word_ok:
                                word_error = (r.stderr or r.stdout or 'Microsoft Word gagal mengekspor PDF.').strip()
                        except Exception as e:
                            word_error = str(e)

                # PRIORITAS 2: LibreOffice sebagai fallback server-side.
                # Tidak ada browser/canvas fallback karena itu dapat mengubah
                # posisi teks, font, margin, tabel, kop, TTD, dan stempel.
                if not word_ok:
                    soffice = shutil.which('soffice') or shutil.which('libreoffice')
                    if soffice:
                        try:
                            r = subprocess.run(
                                [soffice, '--headless', '--convert-to', 'pdf', '--outdir', td, src],
                                capture_output=True, text=True, timeout=120
                            )
                            word_ok = (r.returncode == 0 and os.path.isfile(pdf) and os.path.getsize(pdf) > 0)
                            if not word_ok:
                                word_error = (r.stderr or r.stdout or 'LibreOffice gagal mengekspor PDF.').strip()
                        except Exception as e:
                            word_error = str(e)

                if not word_ok:
                    return json_out(self, 503, {
                        'error': 'PDF tidak dibuat agar layout DOCX tidak berubah. '
                                 'Instal Microsoft Word (disarankan) atau LibreOffice pada komputer server.',
                        'detail': word_error
                    })

                with open(pdf, 'rb') as f:
                    b = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/pdf')
                self.send_header('Content-Disposition', 'attachment; filename="surat.pdf"')
                self.send_header('Content-Length', str(len(b)))
                self.end_headers()
                self.wfile.write(b)
                return

        # Endpoint API lain menerima JSON.
        try:
            raw_json = self.rfile.read(n)
            data = json.loads(raw_json or '{}')
        except Exception as e:
            return json_out(self, 400, {'error': 'JSON tidak valid: ' + str(e)})

        c = db()
        try:
            if p == '/api/counters/reserve':
                code = str(data.get('code', '')).strip()
                if not code:
                    return json_out(self, 400, {'error': 'code wajib'})
                row = c.execute('SELECT value FROM counters WHERE code=?', (code,)).fetchone()
                nxt = (row['value'] if row else 0) + 1
                c.execute(
                    'INSERT INTO counters(code,value) VALUES(?,?) '
                    'ON CONFLICT(code) DO UPDATE SET value=excluded.value',
                    (code, nxt)
                )
                c.commit()
                return json_out(self, 200, {'code': code, 'value': nxt})

            if p == '/api/history':
                c.execute(
                    'INSERT INTO history(nomor,hal,kepada,tanggal) VALUES(?,?,?,?)',
                    (data.get('nomor', ''), data.get('hal', ''), data.get('kepada', ''), data.get('tanggal', ''))
                )
                c.commit()
                return json_out(self, 200, {'ok': True})

            if p == '/api/history/delete':
                c.execute('DELETE FROM history WHERE id=?', (int(data.get('id')),))
                c.commit()
                return json_out(self, 200, {'ok': True})

            if p == '/api/history/clear':
                c.execute('DELETE FROM history')
                c.commit()
                return json_out(self, 200, {'ok': True})
        except Exception as e:
            c.rollback()
            return json_out(self, 500, {'error': str(e)})
        finally:
            c.close()
        self.send_error(404)

if __name__=='__main__':
    port=8765
    print(f'Sistem Surat IKAMI berjalan di http://127.0.0.1:{port}')
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
