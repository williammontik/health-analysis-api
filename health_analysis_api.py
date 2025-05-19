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

# ── Flask Setup ─────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.DEBUG)

# ── SMTP & OpenAI Setup ─────────────────────────────────────────────────────
SMTP_SERVER   = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USERNAME = "kata.chatbot@gmail.com"
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
client = OpenAI(api_key=OPENAI_API_KEY)

# ── Condition‐Specific Approaches ─────────────────────────────────────────────
CONDITION_APPROACHES = {
    "High Blood Pressure": [
        "Adopt a DASH-style diet rich in fruits, vegetables, and low-fat dairy.",
        "Engage in at least 150 minutes/week of moderate aerobic exercise.",
        "Practice daily stress-reduction (e.g. meditation or yoga)."
    ],
    "Low Blood Pressure": [
        "Increase dietary salt intake within safe limits.",
        "Stay well-hydrated and include small, frequent meals.",
        "Add gentle strength training to improve vascular tone."
    ],
    "Diabetes": [
        "Monitor carbohydrate portions and choose low-GI foods.",
        "Incorporate resistance training 2–3 times/week.",
        "Check blood sugar regularly and adjust diet accordingly."
    ],
    "High Cholesterol": [
        "Choose plant-based proteins and reduce saturated fats.",
        "Add 30 minutes of brisk walking daily.",
        "Include omega-3 rich foods (e.g. fatty fish, flaxseeds)."
    ],
    "Skin Problem": [
        "Use gentle, fragrance-free cleansers and moisturizers.",
        "Incorporate a dermatologist-recommended topical (e.g. ceramides).",
        "Maintain a balanced diet rich in antioxidants."
    ],
    "Other": [
        "Maintain a balanced diet and regular exercise.",
        "Ensure adequate sleep (7–9 hours/night).",
        "Stay hydrated and manage stress."
    ]
}

def send_email(html_body: str):
    """Send HTML email containing the AI report and submission details."""
    msg = MIMEText(html_body, 'html')
    msg["Subject"] = "New Global Health Insights Submission"
    msg["From"]    = SMTP_USERNAME
    msg["To"]      = SMTP_USERNAME

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
            smtp.send_message(msg)
        app.logger.info("✅ Email sent successfully.")
    except Exception:
        app.logger.exception("❌ Failed to send email.")

@app.route("/health_analyze", methods=["POST"])
def health_analyze():
    data = request.get_json(force=True)
    try:
        # 1) Extract & sanitize inputs
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

        # 2) Compute age from DOB
        try:
            bd    = datetime.fromisoformat(dob_str)
            today = datetime.today()
            age   = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
        except Exception:
            age = None

        # 3) Compute metrics in Python
        bmi  = round(weight / ((height / 100) ** 2), 1) if height > 0 else None
        syst = random.randint(110, 160)
        chol = random.randint(150, 260)

        metrics = [
            {
                "title": "BMI Status",
                "labels": [f"Similar Age (Age {age})", "Ideal (22)", "High-Risk (30)"],
                "values": [bmi or 0, 22, 30]
            },
            {
                "title": "Blood Pressure (mmHg)",
                "labels": [f"Similar Age (Age {age})", "Optimal (120/80)", "High-Risk (140/90)"],
                "values": [syst, 120, 140]
            },
            {
                "title": "Cholesterol (mg/dL)",
                "labels": [f"Similar Age (Age {age})", "Optimal (<200)", "High-Risk (240+)"],
                "values": [chol, 200, 240]
            }
        ]

        # 4) Build condition‐specific recommendations
        approaches = CONDITION_APPROACHES.get(condition, CONDITION_APPROACHES["Other"])
        approach_md = "\n".join(f"- {a}" for a in approaches)

        # 5) Build GPT prompt
        prompt = f"""
You are generating a GLOBAL HEALTH INSIGHTS report for a generic person of:
- Age: {age}
- Gender: {gender}
- Country: {country}

Their metrics are:
- BMI: {bmi}
- Blood Pressure: {syst} mmHg
- Cholesterol: {chol} mg/dL

Main Concern: {condition}
Details: {details}

Please output a **markdown** report with these sections:

### Demographics
List age, gender, and country.

### Metrics Table
Describe each metric with the labels and values.

### Comparison with Regional & Global Trends
One paragraph comparing these values to typical regional/global benchmarks.

### 🔍 Key Findings
Three bullet points summarizing the insights.

### 🔧 Recommended Approaches for Similar Age (Age {age}), {gender}, in {country} and Globally
{approach_md}

Do **not** mention the person’s name or any identifying info.
"""

        # 6) Call OpenAI for analysis
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        analysis = response.choices[0].message.content.strip()

        # 7) Send email summary
        email_html = (
            "<html><body style='font-family:sans-serif;color:#333'>"
            "<h2>🌐 New Global Health Insights Request</h2>"
            f"<pre style='white-space:pre-wrap'>{analysis}</pre>"
            "</body></html>"
        )
        send_email(email_html)

        # 8) Return JSON to widget
        return jsonify({"metrics": metrics, "analysis": analysis})

    except Exception as e:
        app.logger.exception("Error in /health_analyze")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
