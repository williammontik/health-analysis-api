import os, json, smtplib, logging, random
from datetime import datetime
from email.mime.text import MIMEText
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.DEBUG)

SMTP_SERVER    = "smtp.gmail.com"
SMTP_PORT      = 587
SMTP_USERNAME  = "kata.chatbot@gmail.com"
SMTP_PASSWORD  = os.getenv("SMTP_PASSWORD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set")
client = OpenAI(api_key=OPENAI_API_KEY)

def send_email(html: str):
    msg = MIMEText(html, 'html')
    msg["Subject"] = "New Global Health Insights Submission"
    msg["From"]    = SMTP_USERNAME
    msg["To"]      = SMTP_USERNAME
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
            s.starttls()
            s.login(SMTP_USERNAME, SMTP_PASSWORD)
            s.send_message(msg)
        app.logger.info("✅ Email sent.")
    except Exception:
        app.logger.exception("❌ Email failed")

@app.route("/health_analyze", methods=["POST"])
def health_analyze():
    d = request.get_json(force=True)
    # Extract & compute
    dob       = d.get("dob", "")
    gender    = d.get("gender", "")
    height    = float(d.get("height", 0))
    weight    = float(d.get("weight", 0))
    country   = d.get("country", "")
    condition = d.get("condition", "")
    details   = d.get("details", "")
    lang      = d.get("lang", "en").lower()

    # Age & BMI
    try:
        bd    = datetime.fromisoformat(dob)
        today = datetime.today()
        age   = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
    except:
        age = None
    bmi  = round(weight / ((height/100)**2), 1) if height>0 else 0

    # Random vitals
    syst = random.randint(110,160)
    chol = random.randint(150,260)

    # Metrics array for both widget JSON and email bars
    labels_base = f"Similar Age (Age {age})"
    metrics = [
      {"title":"BMI Status",       "labels":[labels_base,"Ideal (22)","High-Risk (30)"],    "values":[bmi, 22, 30]},
      {"title":"Blood Pressure",   "labels":[labels_base,"Optimal (120)","High-Risk (140)"], "values":[syst,120,140]},
      {"title":"Cholesterol",      "labels":[labels_base,"Optimal (200)","High-Risk (240)"], "values":[chol,200,240]}
    ]

    # GPT prompt per lang
    if lang=="zh":
        header = "您正在查看一份全球健康洞察报告"
        prompt = f"""
生成一份面向年齡約 {age}、性別 {gender}、地區 {country} 的全球健康洞察報告。
指標:
- BMI：{bmi}
- 血壓：{syst} mmHg
- 膽固醇：{chol} mg/dL
主要關注：{condition}
詳細信息：{details}

請輸出 Markdown，包含:
1. 人口統計（年齡/性別/國家）
2. 指標表格
3. 區域 vs 全球 比較
4. 🔍 關鍵發現 3 點
5. 🔧 建議措施 3 條
不要提及個人信息。
"""
    elif lang=="tw":
        header = "您正在查看一份全球健康洞察報告"
        prompt = f"""
生成一份面向年齡約 {age}、性別 {gender}、地區 {country} 的全球健康洞察報告。
指標：
- BMI：{bmi}
- 血壓：{syst} mmHg
- 膽固醇：{chol} mg/dL
主要關注：{condition}
詳細信息：{details}

請輸出 Markdown，包含：
1. 人口統計（年齡/性別/國家）
2. 指標表格
3. 區域 vs 全球 比較
4. 🔍 關鍵發現 3 點
5. 🔧 建議措施 3 條
不要提及個人資料。
"""
    else:
        header = "You are viewing a Global Health Insights report"
        prompt = f"""
Generate a GLOBAL HEALTH INSIGHTS report for:
- Age: {age}
- Gender: {gender}
- Country: {country}

Metrics:
- BMI: {bmi}
- Blood Pressure: {syst} mmHg
- Cholesterol: {chol} mg/dL

Main Concern: {condition}
Details: {details}

Output Markdown with:
1. Demographics
2. Metrics table
3. Regional vs. Global comparison
4. 🔍 Key Findings (3)
5. 🔧 Recommended Approaches (3)

Do NOT include any personal identifiers.
"""

    # Call OpenAI
    resp = client.chat.completions.create(
      model="gpt-3.5-turbo",
      messages=[{"role":"user","content":prompt}]
    )
    analysis = resp.choices[0].message.content.strip()

    # Build email HTML
    # Start with header & analysis
    html = [f"<html><body style='font-family:sans-serif;color:#333'>",
            f"<h2>{header}</h2>",
            "<hr>",
            "<h3>📊 Analysis</h3>",
            f"<pre style='white-space:pre-wrap'>{analysis}</pre>",
            "<h3>📈 Metrics</h3>"]
    # Inline-CSS bar charts
    palette = ["#5E9CA0","#FF9F40","#9966FF"]
    for m in metrics:
        html.append(f"<h4 style='margin-bottom:4px'>{m['title']}</h4>")
        for idx, lbl in enumerate(m["labels"]):
            val = m["values"][idx]
            pct = max(float(val),0)
            color = palette[idx % len(palette)]
            html.append(f"""
  <div style="margin:4px 0; font-size:14px; line-height:1.4">
    {lbl}:
    <span style="
      display:inline-block;
      width:{pct}%;
      height:12px;
      background:{color};
      border-radius:4px;
      vertical-align:middle;
    "></span>
    &nbsp;{pct}%
  </div>
""")
    html.append("</body></html>")

    send_email("".join(html))
    return jsonify({"metrics":metrics,"analysis":analysis})


if __name__=="__main__":
    app.run(host="0.0.0.0", debug=True)
