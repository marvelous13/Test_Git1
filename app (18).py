"""
============================================================
  Sales Processor — Web App (FastAPI)
============================================================
วิธีติดตั้งและรัน:
  pip install fastapi uvicorn python-multipart

  python app.py
  หรือ
  uvicorn app:app --host 0.0.0.0 --port 8000

เปิดเบราว์เซอร์:
  http://localhost:8000
  หรือ http://<server-ip>:8000
============================================================
"""

import os
import re
import uuid
import shutil
import tempfile
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

# import logic จาก sales_processor.py
import sales_processor as sp

BASE_DIR   = Path(__file__).parent.resolve()
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

PARTNERS = {
    "beautrium": "Beautrium",
    "jealeng":   "Jealeng",
    "cj":        "CJ",
    "kis":       "KIS",
    "konvy":     "Konvy",
    "watson":    "Watson",
}

app = FastAPI(title="Sales Processor")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def send_email(partner, output_files, mmyy):
    print("  [EMAIL] Starting... partner=" + partner + " mmyy=" + str(mmyy) + " files=" + str(len(output_files)))
    try:
        cfg_path = BASE_DIR / "config_sql_n8n.json"
        if not cfg_path.exists():
            print("  [EMAIL] ไม่พบ config file:", str(cfg_path))
            return
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        sender   = cfg.get("email_sender")
        password = cfg.get("email_password")
        receiver = cfg.get("email_receiver")
        print("  [EMAIL] sender=" + str(sender) + " receiver=" + str(receiver))
        if not all([sender, password, receiver]):
            print("  [EMAIL] ไม่พบ email config")
            return
        partner_name = partner.capitalize()
        try:
            month_num = int(mmyy[:2])
            year_num  = int("20" + mmyy[2:])
            month_str = datetime(year_num, month_num, 1).strftime("%b %Y")
        except Exception:
            month_str = mmyy
        subject = "Sales " + partner_name + " " + month_str
        msg = MIMEMultipart()
        msg["From"]    = sender
        msg["To"]      = receiver
        msg["Subject"] = subject
        rows_info = ", ".join([fi["name"] + " (" + str(fi["rows"]) + " rows)" for fi in output_files])
        body_text = "Sales Processor - " + partner_name + "\n\nFiles: " + rows_info + "\nGenerated: " + datetime.now().strftime("%d %b %Y %H:%M")
        msg.attach(MIMEText(body_text, "plain"))
        for finfo in output_files:
            fp_path = OUTPUT_DIR / finfo["id"]
            if not fp_path.exists():
                continue
            with open(fp_path, "rb") as fp:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(fp.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment; filename=" + finfo["name"])
            msg.attach(part)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
        print("  [EMAIL] sent to " + receiver + " | " + subject)
    except Exception as e:
        print("  [EMAIL] Error: " + str(e))





# ใช้ absolute path เสมอ ป้องกันปัญหาเมื่อ os.chdir()



HTML = """<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sales Processor</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:       #0f0f0f;
    --surface:  #1a1a1a;
    --border:   #2a2a2a;
    --accent:   #E2711D;
    --accent2:  #f59347;
    --text:     #e8e8e8;
    --muted:    #666;
    --success:  #2ecc71;
    --error:    #e74c3c;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'IBM Plex Sans Thai', sans-serif;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 48px 20px;
  }

  /* header */
  .header { text-align: center; margin-bottom: 48px; }
  .header h1 {
    font-size: 28px;
    font-weight: 600;
    letter-spacing: -0.5px;
    color: #fff;
  }
  .header h1 span { color: var(--accent); }
  .header p { color: var(--muted); margin-top: 8px; font-size: 14px; }

  /* card */
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 32px;
    width: 100%;
    max-width: 560px;
  }

  /* partner select */
  .label {
    font-size: 12px;
    font-weight: 500;
    color: var(--muted);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 10px;
    display: block;
  }
  .partner-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 28px;
  }
  .partner-btn {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    color: var(--text);
    font-family: inherit;
    font-size: 13px;
    font-weight: 500;
    padding: 12px 8px;
    cursor: pointer;
    transition: all 0.15s;
    text-align: center;
  }
  .partner-btn:hover { border-color: var(--accent); color: var(--accent); }
  .partner-btn.active {
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
  }

  /* dropzone */
  .dropzone {
    border: 1.5px dashed var(--border);
    border-radius: 12px;
    padding: 36px 24px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
    margin-bottom: 28px;
    position: relative;
  }
  .dropzone:hover, .dropzone.drag { border-color: var(--accent); background: rgba(226,113,29,0.04); }
  .dropzone input { position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; }
  .dropzone-icon { font-size: 32px; margin-bottom: 12px; }
  .dropzone-text { font-size: 14px; color: var(--muted); }
  .dropzone-text strong { color: var(--accent); }
  .file-name {
    margin-top: 10px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    color: var(--accent2);
    word-break: break-all;
  }

  /* submit btn */
  .submit-btn {
    width: 100%;
    background: var(--accent);
    border: none;
    border-radius: 10px;
    color: #fff;
    font-family: inherit;
    font-size: 15px;
    font-weight: 600;
    padding: 16px;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }
  .submit-btn:hover { background: var(--accent2); transform: translateY(-1px); }
  .submit-btn:disabled { background: var(--border); color: var(--muted); cursor: not-allowed; transform: none; }

  /* status */
  .status {
    margin-top: 20px;
    border-radius: 10px;
    padding: 16px 20px;
    font-size: 13px;
    display: none;
  }
  .status.loading {
    display: flex; align-items: center; gap: 12px;
    background: rgba(226,113,29,0.08);
    border: 1px solid rgba(226,113,29,0.2);
    color: var(--accent2);
  }
  .status.success {
    display: block;
    background: rgba(46,204,113,0.08);
    border: 1px solid rgba(46,204,113,0.2);
    color: var(--success);
  }
  .status.error {
    display: block;
    background: rgba(231,76,60,0.08);
    border: 1px solid rgba(231,76,60,0.2);
    color: var(--error);
  }

  /* download list */
  .download-list { margin-top: 12px; display: flex; flex-direction: column; gap: 8px; }
  .download-btn {
    display: flex; align-items: center; justify-content: space-between;
    background: rgba(46,204,113,0.08);
    border: 1px solid rgba(46,204,113,0.25);
    border-radius: 8px;
    padding: 10px 14px;
    color: var(--success);
    text-decoration: none;
    font-size: 13px;
    font-family: 'IBM Plex Mono', monospace;
    transition: background 0.15s;
  }
  .download-btn:hover { background: rgba(46,204,113,0.15); }

  /* spinner */
  @keyframes spin { to { transform: rotate(360deg); } }
  .spinner {
    width: 18px; height: 18px;
    border: 2px solid rgba(226,113,29,0.3);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    flex-shrink: 0;
  }

  /* log */
  .log {
    margin-top: 12px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: var(--muted);
    max-height: 140px;
    overflow-y: auto;
    white-space: pre-wrap;
    display: none;
  }
  .log.show { display: block; }

  .divider { border: none; border-top: 1px solid var(--border); margin: 24px 0; }
  .footer { margin-top: 40px; font-size: 12px; color: var(--muted); }
</style>
</head>
<body>

<div class="header">
  <h1>Sales <span>Processor</span></h1>
  <p>แปลงไฟล์ยอดขายทุกช่องทางเป็น output มาตรฐาน</p>
</div>

<div class="card">
  <span class="label">เลือกคู่ค้า</span>
  <div class="partner-grid" id="partnerGrid">
    <button class="partner-btn" data-id="beautrium">Beautrium</button>
    <button class="partner-btn" data-id="jealeng">Jealeng</button>
    <button class="partner-btn" data-id="cj">CJ</button>
    <button class="partner-btn" data-id="kis">KIS</button>
    <button class="partner-btn" data-id="konvy">Konvy</button>
    <button class="partner-btn" data-id="watson">Watson</button>
  </div>

  <hr class="divider">

  <span class="label">อัปโหลดไฟล์ยอดขาย</span>
  <div class="dropzone" id="dropzone">
    <input type="file" id="fileInput" accept=".xlsx,.xls">
    <div class="dropzone-icon">📂</div>
    <div class="dropzone-text">วางไฟล์ที่นี่ หรือ <strong>คลิกเพื่อเลือก</strong></div>
    <div class="dropzone-text" style="margin-top:4px;font-size:12px;">.xlsx / .xls</div>
    <div class="file-name" id="fileName"></div>
  </div>

  <div id="dateSection" style="display:none;margin-bottom:20px;">
    <hr class="divider" style="margin:0 0 20px 0;">
    <span class="label">วันที่ของข้อมูล <span style="color:var(--accent)">*</span></span>
    <input type="date" id="fixedDate" oninput="checkReady()" style="
      width:100%; padding:12px 14px; border-radius:10px;
      background:var(--bg); border:1px solid var(--border);
      color:var(--text); font-family:inherit; font-size:14px;
      margin-top:4px; outline:none; cursor:pointer;
    ">
    <div style="font-size:11px;color:var(--muted);margin-top:6px;">
      กรุณากรอกวันที่ของข้อมูล (บังคับ)
    </div>
  </div>

  <button class="submit-btn" id="submitBtn" disabled onclick="processFile()">
    <span>⚡ Process</span>
  </button>

  <div class="status loading" id="statusLoading">
    <div class="spinner"></div>
    <span id="loadingText">กำลังประมวลผล...</span>
  </div>

  <div class="status success" id="statusSuccess">
    <div style="font-weight:600;margin-bottom:8px;">✓ สำเร็จ</div>
    <div class="download-list" id="downloadList"></div>
  </div>

  <div class="status error" id="statusError">
    <div style="font-weight:600;margin-bottom:4px;">✗ เกิดข้อผิดพลาด</div>
    <div id="errorMsg"></div>
  </div>

  <div class="log" id="logBox"></div>
</div>

<div class="footer">Grand Cos Group · Sales Processor v1.0</div>

<script>
let selectedPartner = null;
let selectedFile    = null;

// Partner selection
document.querySelectorAll('.partner-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.partner-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    selectedPartner = btn.dataset.id;
    const needsFixedDate = ['jealeng', 'cj', 'konvy'];
    document.getElementById('dateSection').style.display =
        needsFixedDate.includes(selectedPartner) ? 'block' : 'none';
    if (!needsFixedDate.includes(selectedPartner)) {
        document.getElementById('fixedDate').value = '';
    }
    checkReady();
  });
});

// File input
const fileInput = document.getElementById('fileInput');
const dropzone  = document.getElementById('dropzone');

fileInput.addEventListener('change', e => {
  selectedFile = e.target.files[0];
  document.getElementById('fileName').textContent = selectedFile ? selectedFile.name : '';
  checkReady();
});

dropzone.addEventListener('dragover',  e => { e.preventDefault(); dropzone.classList.add('drag'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag'));
dropzone.addEventListener('drop', e => {
  e.preventDefault();
  dropzone.classList.remove('drag');
  selectedFile = e.dataTransfer.files[0];
  document.getElementById('fileName').textContent = selectedFile ? selectedFile.name : '';
  checkReady();
});

function checkReady() {
    const needsDate = ['jealeng', 'cj', 'konvy'];
    const dateOk = !needsDate.includes(selectedPartner) || document.getElementById('fixedDate').value;
    document.getElementById('submitBtn').disabled = !(selectedPartner && selectedFile && dateOk);
}

function setStatus(type) {
  ['loading','success','error'].forEach(t => {
    document.getElementById('status' + t.charAt(0).toUpperCase() + t.slice(1)).style.display = 'none';
  });
  if (type) document.getElementById('status' + type.charAt(0).toUpperCase() + type.slice(1)).style.display =
    type === 'loading' ? 'flex' : 'block';
}

async function processFile() {
  if (!selectedPartner || !selectedFile) return;

  const btn = document.getElementById('submitBtn');
  btn.disabled = true;
  setStatus('loading');
  document.getElementById('logBox').classList.remove('show');
  document.getElementById('downloadList').innerHTML = '';

  const formData = new FormData();
  formData.append('partner', selectedPartner);
  formData.append('file', selectedFile);
  const fixedDateVal = document.getElementById('fixedDate') ? document.getElementById('fixedDate').value : '';
  if (fixedDateVal) formData.append('fixed_date', fixedDateVal);

  try {
    document.getElementById('loadingText').textContent = `กำลังประมวลผล ${selectedFile.name} ...`;
    const res  = await fetch('/process', { method: 'POST', body: formData });
    const data = await res.json();

    if (!res.ok || data.error) {
      setStatus('error');
      document.getElementById('errorMsg').textContent = data.error || 'Unknown error';
      if (data.log) {
        document.getElementById('logBox').textContent = data.log;
        document.getElementById('logBox').classList.add('show');
      }
    } else {
      setStatus('success');
      data.files.forEach(f => {
        const a = document.createElement('a');
        a.className = 'download-btn';
        a.href      = `/download/${f.id}`;
        a.download  = f.name;
        a.innerHTML = `<span>⬇ ${f.name}</span><span style="font-size:11px;opacity:0.7">${f.rows} rows</span>`;
        document.getElementById('downloadList').appendChild(a);
      });
      if (data.log) {
        document.getElementById('logBox').textContent = data.log;
        document.getElementById('logBox').classList.add('show');
      }
    }
  } catch (err) {
    setStatus('error');
    document.getElementById('errorMsg').textContent = err.message;
  } finally {
    btn.disabled = false;
  }
}
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML


@app.post("/process")
async def process(partner: str = Form(...), file: UploadFile = File(...), fixed_date: str = Form(None)):
    if partner not in PARTNERS:
        raise HTTPException(400, f"ไม่รู้จัก partner: {partner}")

    # บันทึกไฟล์ upload
    job_id   = str(uuid.uuid4())[:8]
    work_dir = UPLOAD_DIR / job_id
    work_dir.mkdir(parents=True, exist_ok=True)

    upload_path = work_dir / file.filename
    with open(upload_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # redirect stdout เพื่อเก็บ log
    import io, sys
    old_stdout = sys.stdout
    sys.stdout = buf = io.StringIO()

    output_files = []
    try:
        cfg         = sp.PARTNER_CONFIG[partner]
        conn        = sp.get_sql_connection()
        master_map  = sp.load_customer_master(conn) if cfg['join_master']  else {}
        product_map = sp.load_product_master(conn)  if cfg['join_product'] else {}
        conn.close()

        mmyy = sp.get_mmyy(str(upload_path))
        if mmyy == 'MMYY' and fixed_date:
            mmyy = sp.get_mmyy_from_fixed_date(fixed_date)
        # fallback: ดึง mmyy จากชื่อไฟล์ output ที่ได้
        if mmyy == 'MMYY':
            import re as _re
            m = _re.search(r'_(\d{4})\.xlsx', str(upload_path.name))
            if m and int(m.group(1)[:2]) <= 12:
                mmyy = m.group(1)

        # เปลี่ยน cwd ไปที่ work_dir ชั่วคราว แล้วกลับมา
        orig_cwd = os.getcwd()
        os.chdir(str(work_dir))
        try:
            if partner == 'beautrium':
                sp.process_beautrium(upload_path.name, master_map, mmyy, fixed_date=fixed_date)
            elif partner == 'jealeng':
                sp.process_jealeng(upload_path.name, product_map, mmyy, fixed_date=fixed_date)
            elif partner == 'cj':
                sp.process_cj(upload_path.name, product_map, mmyy, fixed_date=fixed_date)
            elif partner == 'kis':
                sp.process_kis(upload_path.name, master_map, mmyy, fixed_date=fixed_date)
            elif partner == 'konvy':
                sp.process_konvy(str(upload_path), fixed_date=fixed_date)
            elif partner == 'watson':
                sp.process_watson(upload_path.name, product_map, mmyy, fixed_date=fixed_date)
        finally:
            os.chdir(orig_cwd)

        # รวบรวม output files แยก folder ตาม partner
        import pandas as pd
        partner_dir = OUTPUT_DIR / partner
        partner_dir.mkdir(exist_ok=True)
        for f in work_dir.glob("*.xlsx"):
            if f.name == upload_path.name:
                continue
            try:
                df   = pd.read_excel(f)
                rows = len(df)
            except Exception:
                rows = 0
            # copy ไปที่ outputs/<partner>/<filename> ไม่มี job_id
            out_path = partner_dir / f.name
            shutil.copy(f, out_path)
            output_files.append({"id": f"{partner}/{f.name}", "name": f.name, "rows": rows})

    except Exception as e:
        sys.stdout = old_stdout
        log = buf.getvalue()
        return {"error": str(e), "log": log}
    finally:
        sys.stdout = old_stdout
        shutil.rmtree(work_dir, ignore_errors=True)

    log = buf.getvalue()

    # ส่ง email อัตโนมัติ
    if output_files:
        # ถ้า mmyy ยังเป็น MMYY ให้ดึงจากชื่อไฟล์ output
        if mmyy == 'MMYY':
            import re as _re
            for fi in output_files:
                m = _re.search(r'_(\d{4})\.xlsx', fi['name'])
                if m and int(m.group(1)[:2]) <= 12:
                    mmyy = m.group(1)
                    break
        send_email(partner, output_files, mmyy)

    return {"files": output_files, "log": log}


@app.get("/download/{file_path:path}")
async def download(file_path: str):
    safe_path = re.sub(r'[^a-zA-Z0-9_\-./]', '', file_path)
    out_path  = OUTPUT_DIR / safe_path
    if not out_path.exists():
        raise HTTPException(404, "ไม่พบไฟล์")
    return FileResponse(out_path, filename=out_path.name,
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ─────────────────────────────────────────
# RUN
# ─────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
