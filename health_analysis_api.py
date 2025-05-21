# -*- coding: utf-8 -*-
import os
import random
from datetime import datetime
from dateutil import parser
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from email.mime.text import MIMEText
import smtplib

app = Flask(__name__)
CORS(app)

# ── OpenAI Configuration ─────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set")
client = OpenAI(api_key=OPENAI_API_KEY)

# ── SMTP Configuration ───────────────────────────────────────────────────────
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT   = 587
SMTP_USER   = "kata.chatbot@gmail.com"
SMTP_PASS   = os.getenv("SMTP_PASSWORD")

def compute_age_from_dob(dob_str: str) -> int:
    try:
        bd = parser.parse(dob_str)
    except Exception:
        return None
    today = datetime.today()
    return today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))

def send_email(body: str):
    msg = MIMEText(body, 'html')
    msg["Subject"] = "Your AI Health Report"
    msg["From"]    = SMTP_USER
    msg["To"]      = SMTP_USER
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
        s.starttls()
        if SMTP_PASS:
            s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)

@app.route("/health_analyze", methods=["POST"])
def health_analyze():
    d = request.get_json(force=True)
    # Extract inputs
    name      = d.get('name','')
    dob       = d.get('dob','')
    age       = compute_age_from_dob(dob) or ''
    gender    = d.get('gender','')
    height    = d.get('height','')
    weight    = d.get('weight','')
    country   = d.get('country','')
    condition = d.get('condition','')
    details   = d.get('details','')
    referrer  = d.get('referrer','')
    angel     = d.get('angel','')

    # Generate random benchmarks: (local, regional, global)
    def rv(): return random.randint(50, 100)
    metrics = [
        ("Blood Pressure Health", rv(), rv(), rv()),
        ("Blood Sugar Control",    rv(), rv(), rv()),
        ("Cholesterol Management", rv(), rv(), rv()),
    ]

    # Build horizontal bars
    bar_html = ""
    for title, local, regional, glob in metrics:
        bar_html += f"<strong>{title}</strong><br>"
        for val, color in [(local,"#5E9CA0"), (regional,"#FF9F40"), (glob,"#9966FF")]:
            bar_html += (
                f"<span style='display:inline-block; width:{val}%; height:12px; "
                f"background:{color}; margin-right:6px; border-radius:4px;'></span> {val}%<br>"
            )
        bar_html += "<br>"

    # Static summary
    summary_html = (
        f"<h2>📄 Health Summary for {name}</h2>"
        f"• Age: {age}<br>"
        f"• Gender: {gender}<br>"
        f"• Height: {height} cm, Weight: {weight} kg<br>"
        f"• Country: {country}<br>"
        f"• Main Concern: {condition}<br>"
        f"• Details: {details}<br>"
        f"• Referrer: {referrer}<br>"
        f"• Caring Angel: {angel}<br><br>"
    )

    # OpenAI prompt
    local_bp, reg_bp, glob_bp = metrics[0][1], metrics[0][2], metrics[0][3]
    prompt = (
        f"Generate seven health-focused analytical paragraphs as a global overview for {gender}s aged {age} in {country}. "
        f"Reference Blood Pressure Health: {local_bp}% local, {reg_bp}% regional, {glob_bp}% global; "
        f"Blood Sugar Control: {metrics[1][1]}%/{metrics[1][2]}%/{metrics[1][3]}%; "
        f"Cholesterol Management: {metrics[2][1]}%/{metrics[2][2]}%/{metrics[2][3]}%. "
        f"Incorporate the main concern ({condition}) and details provided. "
        f"Wrap each paragraph in <p>…</p> and use transitions like 'Conversely', 'Meanwhile'."
    )

    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an expert health analyst aware of regional and global benchmarks."},
            {"role": "user",   "content": prompt}
        ],
        temperature=0.7,
    )
    analysis_html = resp.choices[0].message.content

    full_html = bar_html + summary_html + "<h4>🌐 Global Health Analysis</h4>" + analysis_html
    send_email(full_html)

    return jsonify({
        "metrics": [
            {"title": t, "labels": ["Local","Regional","Global"], "values": [l, r, g]}
            for t, l, r, g in metrics
        ],
        "analysis": full_html
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
