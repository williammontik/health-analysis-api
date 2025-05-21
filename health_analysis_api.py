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
    msg["Subject"] = "Your Global Health Insights Report"
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
    dob       = d.get("dob", "")
    gender    = d.get("gender", "")
    height    = float(d.get("height", 0))
    weight    = float(d.get("weight", 0))
    country   = d.get("country", "")
    condition = d.get("condition", "")
    details   = d.get("details", "")
    lang      = d.get("lang", "en").lower()

    try:
        bd    = datetime.fromisoformat(dob)
        today = datetime.today()
        age   = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
    except:
        age = None
    bmi  = round(weight / ((height/100)**2), 1) if height > 0 else 0
    syst = random.randint(110,160)
    chol = random.randint(150,260)

    metrics = [
        {"title": "BMI Status",       "labels": [f"Age {age}", "Ideal (22)", "High-Risk (30)"],    "values": [bmi, 22, 30]},
        {"title": "Blood Pressure",   "labels": [f"Age {age}", "Optimal (120)", "High-Risk (140)"], "values": [syst, 120, 140]},
        {"title": "Cholesterol",      "labels": [f"Age {age}", "Optimal (200)", "High-Risk (240)"], "values": [chol, 200, 240]}
    ]

    prompt = f"""
Write a public health improvement report based on the following data:
- Age Group: around {age}
- Gender: {gender}
- Country: {country}
- Main Health Concern: {condition}
- Brief Description: {details}
- Key metrics: BMI = {bmi}, Blood Pressure = {syst} mmHg, Cholesterol = {chol} mg/dL

Do NOT personalize to a specific person. Write as if this is an anonymous case study, highlighting general insights from similar individuals. Use professional, constructive tone with suggestions.

Please output 6 clear paragraphs:
1. Demographics summary.
2. Interpretation of BMI and its implication.
3. Comment on blood pressure and potential trends.
4. Cholesterol impact and general advice.
5. Insights drawn from other individuals with similar concern in {country}.
6. Suggested actions or improvements (e.g., diet, exercise, screenings).

Wrap each paragraph in <p>...</p> tags.
"""

    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    analysis = resp.choices[0].message.content.strip()

    # HTML for email and frontend
    html = [f"<html><body style='font-family:sans-serif;'>",
            "<h2 style='color:#5E9CA0;'>🎉 Global Identical Health Insights</h2><hr>",
            "<h3>📊 Metrics Overview</h3>"]
    
    palette = ["#5E9CA0", "#FF9F40", "#9966FF"]
    for m in metrics:
        html.append(f"<h4>{m['title']}</h4>")
        for idx, lbl in enumerate(m["labels"]):
            val = m["values"][idx]
            html.append(f"""
<div style="margin-bottom:6px;">
  {lbl}: 
  <span style='display:inline-block; width:{val}%; height:12px; background:{palette[idx % 3]}; border-radius:4px;'></span> {val}%
</div>""")
    
    html.append("<h3>📄 AI Health Insights</h3>")
    html.append(analysis)
    html.append("</body></html>")

    send_email("".join(html))
    return jsonify({"metrics": metrics, "analysis": analysis})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
