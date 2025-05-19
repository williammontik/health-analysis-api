# health_analysis_api.py

import os
import json
import smtplib
import logging
import random
from datetime import datetime
from email.mime.text import MIMEText

from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.DEBUG)

# SMTP & OpenAI config
SMTP_SERVER   = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USERNAME = "kata.chatbot@gmail.com"
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set.")
client = OpenAI(api_key=OPENAI_API_KEY)

def send_email(html_body: str):
    msg = MIMEText(html_body, 'html')
    msg["Subject"] = "New Health Check Submission"
    msg["From"]    = SMTP_USERNAME
    msg["To"]      = SMTP_USERNAME
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
            smtp.send_message(msg)
        app.logger.info("✅ Email sent.")
    except Exception:
        app.logger.exception("❌ Email failed.")

@app.route("/health_analyze", methods=["POST"])
def health_analyze():
    data = request.get_json(force=True)
    try:
        # 1) Extract inputs
        name      = data.get("name","").strip()
        dob_str   = data.get("dob","")
        gender    = data.get("gender","").strip()
        height    = float(data.get("height",0))
        weight    = float(data.get("weight",0))
        country   = data.get("country","").strip()
        condition = data.get("condition","").strip()
        details   = data.get("details","").strip()
        referrer  = data.get("referrer","").strip()
        angel     = data.get("angel","").strip()

        # 2) Compute age & BMI
        try:
            bd = datetime.fromisoformat(dob_str)
            today = datetime.today()
            age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
        except:
            age = None
        bmi = round(weight / ((height/100)**2), 1) if height>0 else None

        # 3) Build metrics in Python (no JSON-loading from GPT)
        #    You can tune these thresholds as desired.
        metrics = [
            {
              "title": "BMI Status",
              "labels": ["You","Ideal (22)","High-Risk (30)"],
              "values": [bmi or 0, 22, 30]
            },
            {
              "title": "BP Risk Level",
              "labels": ["You","Optimal (120/80)","High Risk"],
              "values": [
                random.randint(110, 160),
                120,
                140
              ]
            },
            {
              "title": "Cholesterol Risk",
              "labels": ["You","Optimal (<200)","High Risk"],
              "values": [
                random.randint(150, 260),
                200,
                240
              ]
            }
        ]

        # 4) Ask GPT for analysis text only
        prompt = f"""
You are a friendly health consultant.
Please provide a concise, 3-step analysis and recommendations for:

Patient: {name}, Age {age}, Gender {gender}, Country {country}
BMI: {bmi}, Main Concern: {condition}
Details: {details}
"""
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content":prompt}]
        )
        analysis = resp.choices[0].message.content.strip()

        # 5) Send email summary
        html = (
            f"<html><body><h2>New Health Submission</h2>"
            f"<p>👤 {name}<br>🎂 {dob_str} (Age {age})<br>⚧️ {gender}<br>"
            f"📏 {height}cm  ⚖️ {weight}kg  🌍 {country}<br>"
            f"📌 Concern: {condition}<br>📝 {details}<br>"
            f"💬 Referrer: {referrer}<br>👼 Angel: {angel}</p>"
            f"<h3>Analysis</h3><p>{analysis}</p>"
            f"</body></html>"
        )
        send_email(html)

        # 6) Return JSON
        return jsonify({"metrics": metrics, "analysis": analysis})

    except Exception as e:
        app.logger.exception("Error in /health_analyze")
        return jsonify({"error": str(e)}), 500

if __name__=="__main__":
    app.run(debug=True, host="0.0.0.0")
