import os, json, smtplib, logging, random
from datetime import datetime
from email.mime.text import MIMEText
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.DEBUG)

SMTP_SERVER   = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USERNAME = "kata.chatbot@gmail.com"
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
OPENAI_API_KEY= os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY: raise RuntimeError("OPENAI_API_KEY not set")
client = OpenAI(api_key=OPENAI_API_KEY)

def send_email(html):
    msg=MIMEText(html,'html')
    msg["Subject"]="New Global Health Insights Submission"
    msg["From"]=SMTP_USERNAME; msg["To"]=SMTP_USERNAME
    try:
        with smtplib.SMTP(SMTP_SERVER,SMTP_PORT) as s:
            s.starttls(); s.login(SMTP_USERNAME,SMTP_PASSWORD); s.send_message(msg)
    except Exception:
        app.logger.exception("Email failed")

@app.route("/health_analyze", methods=["POST"])
def health_analyze():
    d = request.get_json(force=True)
    # Common extraction
    dob, gender, height, weight = d.get("dob",""), d.get("gender",""), float(d.get("height",0)), float(d.get("weight",0))
    country, condition, details = d.get("country",""), d.get("condition",""), d.get("details","")
    lang = d.get("lang","en").lower()
    # Compute age & metrics
    try:
        bd=datetime.fromisoformat(dob); today=datetime.today()
        age=today.year-bd.year-((today.month,today.day)<(bd.month,bd.day))
    except: age=None
    bmi=round(weight/((height/100)**2),1) if height>0 else None
    syst=random.randint(110,160); chol=random.randint(150,260)
    labels = [f"Similar Age (Age {age})","Ideal","High-Risk"]
    metrics=[
      {"title":"BMI Status","labels":[f"Similar Age (Age {age})","Ideal (22)","High-Risk (30)"],"values":[bmi or 0,22,30]},
      {"title":"Blood Pressure","labels":[f"Similar Age (Age {age})","Optimal","High-Risk"],"values":[syst,120,140]},
      {"title":"Cholesterol","labels":[f"Similar Age (Age {age})","Optimal","High-Risk"],"values":[chol,200,240]}
    ]

    # Build prompt per language
    if lang=="zh":
        header="您正在查看一份全球健康洞察报告"
        prompt=f"""
生成一份面向 30 岁左右同龄{gender}在{country}的全球健康洞察报告。
指标：
- BMI：{bmi}
- 血压：{syst} mmHg
- 胆固醇：{chol} mg/dL
主要关注：{condition}
详细信息：{details}

请输出 Markdown，包含：
1. 人口统计（年龄/性别/国家）
2. 指标表格
3. 区域 vs 全球 比较段落
4. 🔍 关键发现 3 点
5. 🔧 建议措施 3 条
不要提及个人信息。
"""
    elif lang=="tw":
        header="您正在查看一份全球健康洞察報告"
        prompt=f"""
生成一份面向 30 歲左右同齡{gender}在{country}的全球健康洞察報告。
指標：
- BMI：{bmi}
- 血壓：{syst} mmHg
- 膽固醇：{chol} mg/dL
主要關注：{condition}
詳細信息：{details}

請輸出 Markdown，包含：
1. 人口統計（年齡/性別/國家）
2. 指標表格
3. 區域 vs 全球 比較段落
4. 🔍 關鍵發現 3 點
5. 🔧 建議措施 3 條
不要提及個人信息。
"""
    else:
        header="You are viewing a Global Health Insights report"
        prompt=f"""
Generate a GLOBAL HEALTH INSIGHTS report for a generic person of:
- Age: {age}
- Gender: {gender}
- Country: {country}

Metrics:
- BMI: {bmi}
- Blood Pressure: {syst} mmHg
- Cholesterol: {chol} mg/dL

Main Concern: {condition}
Details: {details}

Please output Markdown with:
1. Demographics
2. Metrics table
3. Comparison with regional vs. global trends
4. 🔍 Key Findings (3 bullets)
5. 🔧 Recommended Approaches (3 bullets)

Do NOT mention any personal identifiers.
"""

    # Call GPT
    resp = client.chat.completions.create(model="gpt-3.5-turbo",messages=[{"role":"user","content":prompt}])
    analysis = resp.choices[0].message.content.strip()

    # Email & response
    email_html=f"<html><body><h2>{header}</h2><pre>{analysis}</pre></body></html>"
    send_email(email_html)
    return jsonify({"metrics":metrics,"analysis":analysis})

if __name__=="__main__":
    app.run(host="0.0.0.0",debug=True)
