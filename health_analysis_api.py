# -*- coding: utf-8 -*-
import os, random
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from email.mime.text import MIMEText
import smtplib

app = Flask(__name__)
CORS(app)

# OpenAI config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set")
client = OpenAI(api_key=OPENAI_API_KEY)

# SMTP
SMTP_SERVER = "smtp.gmail.com"; SMTP_PORT = 587
SMTP_USER = "kata.chatbot@gmail.com"
SMTP_PASS = os.getenv("SMTP_PASSWORD")

def send_email(body):
    msg = MIMEText(body, 'html')
    msg["Subject"] = "Your AI Health Report"
    msg["From"] = SMTP_USER; msg["To"] = SMTP_USER
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
        s.starttls(); s.login(SMTP_USER, SMTP_PASS); s.send_message(msg)

@app.route("/health_analyze", methods=["POST"])
def health_analyze():
    data = request.json
    name = data.get('name',''); age = data.get('age','')
    gender = data.get('gender',''); concern = data.get('mainConcern','')
    desc = data.get('description',''); lang = data.get('lang','en')

    # random health scores
    def rv(): return random.randint(50,100)
    metrics = [
        ("Heart Health", rv()),
        ("Sleep Quality", rv()),
        ("Stress Levels", rv()),
    ]

    # build bars
    bar_html = ""
    for title, val in metrics:
        bar_html += f"<strong>{title}</strong><br>"
        bar_html += (
            f"<span style='display:inline-block; width:{val}%; height:12px;"
            f" background:#FF6B6B; margin-right:6px; border-radius:4px;'></span> {val}%<br><br>"
        )

    # static report
    report_html = (
        f"<h2>📄 Health Summary for {name}</h2>"
        f"• Age/Gender: {age}/{gender}<br>"
        f"• Main Concern: {concern}<br>"
        f"• Details: {desc}<br><br>"
    )

    # prompt setup
    prompt = (
        f"Generate seven health-focused analytical paragraphs as an industry-style overview, referencing the following metrics: "
        f"Heart Health at {metrics[0][1]}%, Sleep Quality at {metrics[1][1]}%, Stress Levels at {metrics[2][1]}%. "
        f"Address the main concern ({concern}) and description. Wrap each in <p>…</p>. Include transitions like 'Conversely', 'Meanwhile', etc."
    )
    comp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role":"system","content":"You are an expert health analyst."},
            {"role":"user","content":prompt}
        ], temperature=0.7
    )
    analysis = comp.choices[0].message.content

    full_html = bar_html + report_html + f"<h2>🌐 Global Health Analysis</h2>" + analysis
    send_email(full_html)
    return jsonify({"analysis": full_html, "metrics": metrics})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT',5000)))
