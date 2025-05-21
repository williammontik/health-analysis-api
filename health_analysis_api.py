# -*- coding: utf-8 -*-
import os
import random
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from email.mime.text import MIMEText
import smtplib

app = Flask(__name__)
CORS(app)

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set")
client = OpenAI(api_key=OPENAI_API_KEY)

# SMTP configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "kata.chatbot@gmail.com"
SMTP_PASS = os.getenv("SMTP_PASSWORD")

def send_email(body: str):
    msg = MIMEText(body, 'html')
    msg["Subject"] = "Your AI Health Report"
    msg["From"] = SMTP_USER
    msg["To"] = SMTP_USER
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
        s.starttls()
        if SMTP_PASS:
            s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)

@app.route("/health_analyze", methods=["POST"])
def health_analyze():
    data = request.get_json(force=True)
    name        = data.get('name', '')
    age         = data.get('age', '')
    gender      = data.get('gender', '')
    country     = data.get('country', '')
    concern     = data.get('mainConcern', '')
    description = data.get('description', '')
    lang        = data.get('lang', 'en')

    # Generate random health metrics
    def rv(): return random.randint(50, 100)
    metrics = [
        ("Heart Health", rv()),
        ("Sleep Quality", rv()),
        ("Stress Levels", rv()),
    ]

    # Build horizontal bar HTML
    bar_html = ""
    for title, value in metrics:
        bar_html += f"<strong>{title}</strong><br>"
        bar_html += (
            f"<span style='display:inline-block; width:{value}%; "
            f"height:12px; background:#5E9CA0; margin-right:6px; "
            f"border-radius:4px;'></span> {value}%<br><br>"
        )

    # Static summary section
    summary_html = (
        f"<h2>📄 Health Summary (Age {age}, {gender}, {country})</h2>"
        f"• Main Concern: {concern}<br>"
        f"• Description: {description}<br><br>"
    )

    # Build the OpenAI prompt
    prompt = (
        f"Generate seven health-focused analytical paragraphs as a global overview for {gender}s "
        f"aged {age} in {country}, referencing: Heart Health at {metrics[0][1]}%, "
        f"Sleep Quality at {metrics[1][1]}%, Stress Levels at {metrics[2][1]}%. "
        f"Incorporate the main concern ({concern}) and description. Wrap each paragraph in <p>…</p> "
        f"and use transitions like 'Conversely', 'Meanwhile'."
    )

    # Call OpenAI
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an expert health analyst."},
            {"role": "user",   "content": prompt}
        ],
        temperature=0.7,
    )
    analysis_html = response.choices[0].message.content

    # Assemble full HTML
    full_html = (
        bar_html
        + summary_html
        + "<h2>🌐 Global Health Analysis</h2>"
        + analysis_html
    )

    # Send email and return JSON
    send_email(full_html)
    return jsonify({
        "metrics": metrics,
        "analysis": full_html,
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
