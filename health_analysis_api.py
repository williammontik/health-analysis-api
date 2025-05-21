# -*- coding: utf-8 -*-
import os, random
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from email.mime.text import MIMEText
import smtplib

app = Flask(__name__)
CORS(app)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set")
client = OpenAI(api_key=OPENAI_API_KEY)

SMTP_SERVER, SMTP_PORT = "smtp.gmail.com", 587
SMTP_USER = "kata.chatbot@gmail.com"
SMTP_PASS = os.getenv("SMTP_PASSWORD")

def send_email(body):
    msg = MIMEText(body, 'html')
    msg["Subject"] = "Your AI Health Report"
    msg["From"] = SMTP_USER
    msg["To"] = SMTP_USER
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
        s.starttls(); s.login(SMTP_USER, SMTP_PASS); s.send_message(msg)

@app.route("/health_analyze", methods=["POST"])
def health_analyze():
    d = request.get_json(force=True)
    name, age, gender = d.get('name',''), d.get('age',''), d.get('gender','')
    country, concern = d.get('country',''), d.get('mainConcern','')
    desc = d.get('description','')
    lang = d.get('lang','en')

    # Random health metrics
    def rv(): return random.randint(50,100)
    metrics = [("Heart Health", rv()), ("Sleep Quality", rv()), ("Stress Levels", rv())]

    # Bars
    bar_html = ""
    for t,val in metrics:
        bar_html += f"<strong>{t}</strong><br>"
        bar_html += (
            f"<span style='display:inline-block; width:{val}%; height:12px; background:#5E9CA0; margin-right:6px; border-radius:4px;'></span> {val}%<br><br>"
        )

    # Static summary
    report_html = (
        f"<h2>📄 Health Summary (Age {age}, {gender}, {country})</h2>"
        f"• Main Concern: {concern}<br>"
        f"• Details: {desc}<br><br>"
    )

    # Prompt\ n    prompt = (
        f"Generate seven health-focused analytical paragraphs as a global overview for {gender}s aged {age} in {country}, referencing: "
        f"Heart Health {metrics[0][1]}%, Sleep Quality {metrics[1][1]}%, Stress Levels {metrics[2][1]}%. "
        f"Incorporate the main concern ({concern}) and description. Wrap each in <p>…</p> and use transitions like 'Conversely', 'Meanwhile'."
    )

    comp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"system","content":"You are an expert health analyst."},
                  {"role":"user","content":prompt}],
        temperature=0.7
    )
    analysis = comp.choices[0].message.content

    full = bar_html + report_html + f"<h2>🌐 Global Health Analysis</h2>" + analysis
    send_email(full)
    return jsonify({"analysis": full, "metrics": metrics})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT',5000)))
