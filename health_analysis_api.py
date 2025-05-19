# health_analysis_api.py

import os
import json
import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText

from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

# ── Flask Setup ─────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.DEBUG)

# ── SMTP & OpenAI Setup ─────────────────────────────────────────────────────
SMTP_SERVER   = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USERNAME = "kata.chatbot@gmail.com"
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
if not SMTP_PASSWORD:
    app.logger.warning("SMTP_PASSWORD not set; emails may fail.")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
client = OpenAI(api_key=OPENAI_API_KEY)


def send_email(html_body: str):
    """Send HTML email to yourself with submission details and report."""
    msg = MIMEText(html_body, 'html')
    msg["Subject"] = "New Health Check Submission"
    msg["From"] = SMTP_USERNAME
    msg["To"] = SMTP_USERNAME

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
            smtp.send_message(msg)
        app.logger.info("✅ Health submission email sent.")
    except Exception:
        app.logger.exception("❌ Failed to send health submission email.")


@app.route("/health_analyze", methods=["POST"])
def health_analyze():
    data = request.get_json(force=True)
    try:
        # 1) Extract inputs
        name      = data.get("name", "").strip()
        dob_str   = data.get("dob", "")
        gender    = data.get("gender", "").strip()
        height    = float(data.get("height", 0))
        weight    = float(data.get("weight", 0))
        country   = data.get("country", "").strip()
        condition = data.get("condition", "").strip()
        details   = data.get("details", "").strip()
        referrer  = data.get("referrer", "").strip()
        angel     = data.get("angel", "").strip()

        # 2) Compute age & BMI
        try:
            birthdate = datetime.fromisoformat(dob_str)
            today     = datetime.today()
            age = today.year - birthdate.year - (
                (today.month, today.day) < (birthdate.month, birthdate.day)
            )
        except Exception:
            age = None

        bmi = round(weight / ((height / 100) ** 2), 1) if height > 0 else None
        app.logger.debug(f"Computed age={age}, BMI={bmi}")

        # 3) Build OpenAI prompt
        prompt = f"""
You are a friendly health consultant.

Patient Info:
- Name: {name}
- DOB: {dob_str} (Age: {age})
- Gender: {gender}
- Country: {country}
- Height: {height} cm
- Weight: {weight} kg
- BMI: {bmi}

Main Concern: {condition}
Details: {details}
Referrer: {referrer}
Caring Angel: {angel}

Please:
1. Return three JSON metrics comparing the patient vs. ideal vs. high-risk, e.g.:
   {{ "title": "BMI Status", "labels": ["You","Ideal","High-Risk"], "values": [bmi,22,30] }}
2. Provide a concise analysis with three actionable next steps.
3. Output only a single JSON object with keys "metrics" and "analysis".
"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.choices[0].message.content.strip()
        report = json.loads(raw)

        # 4) Build and send email
        html = [
            "<html><body style='font-family:sans-serif;color:#333'>",
            "<h2>🎯 New Health Check Submission</h2>",
            "<p>",
            f"👤 <strong>Given Legal Name:</strong> {name}<br>",
            f"🎂 <strong>Date of Birth:</strong> {dob_str}<br>",
            f"⚧️ <strong>Gender:</strong> {gender}<br>",
            f"📏 <strong>Height:</strong> {height} cm<br>",
            f"⚖️ <strong>Weight:</strong> {weight} kg<br>",
            f"🌍 <strong>Country:</strong> {country}<br>",
            f"📌 <strong>Main Concern:</strong> {condition}<br>",
            f"📝 <strong>Details:</strong> {details}<br>",
            f"💬 <strong>Referrer:</strong> {referrer}<br>",
            f"👼 <strong>Caring Angel:</strong> {angel}<br>",
            "</p><hr>",
            "<h3>📊 Metrics & Analysis</h3>",
            "<pre style='white-space:pre-wrap;'>",
            json.dumps(report, indent=2, ensure_ascii=False),
            "</pre>",
            "</body></html>"
        ]
        send_email("".join(html))

        # 5) Return JSON to widget
        return jsonify(report)

    except Exception as e:
        app.logger.exception("Error in /health_analyze")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
