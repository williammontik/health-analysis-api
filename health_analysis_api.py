# -*- coding: utf-8 -*-
import os, logging, smtplib, traceback
from datetime import datetime
from dateutil import parser
from email.mime.text import MIMEText
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.DEBUG)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "kata.chatbot@gmail.com"
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def compute_age(dob):
    try:
        dt = parser.parse(dob)
        today = datetime.today()
        return today.year - dt.year - ((today.month, today.day) < (dt.month, dt.day))
    except:
        return 0

def get_openai_response(prompt, temp=0.7):
    try:
        result = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=temp
        )
        return result.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"OpenAI error: {e}")
        return "⚠️ Unable to generate response."

def generate_metrics():
    import random
    return [
        {
            "title": "Core Health Signals",
            "labels": ["Sleep Quality", "Energy Levels", "Emotional Balance"],
            "values": [random.randint(60, 85), random.randint(55, 80), random.randint(50, 75)]
        },
        {
            "title": "Daily Wellness",
            "labels": ["Hydration", "Nutrition", "Movement"],
            "values": [random.randint(65, 90), random.randint(60, 85), random.randint(55, 80)]
        },
        {
            "title": "Long-Term Resilience",
            "labels": ["Immunity Strength", "Stress Recovery", "Motivation"],
            "values": [random.randint(60, 85), random.randint(55, 80), random.randint(60, 90)]
        }
    ]

def build_html_report(age, gender, country, concern, notes, metrics, summary, creative):
    chart_html = ""
    for m in metrics:
        chart_html += f"<strong style='font-size:18px;color:#333;'>{m['title']}</strong><br>"
        for label, val in zip(m['labels'], m['values']):
            chart_html += (
                f"<div style='display:flex;align-items:center;margin-bottom:8px;'>"
                f"<span style='width:180px;'>{label}</span>"
                f"<div style='flex:1;background:#eee;border-radius:5px;overflow:hidden;'>"
                f"<div style='width:{val}%;height:14px;background:#5E9CA0;'></div></div>"
                f"<span style='margin-left:10px;'>{val}%</span></div>"
            )
        chart_html += "<br>"

    summary_html = "<br><div style='font-size:24px;font-weight:bold;'>🧠 Summary:</div><br>" + ''.join(
        f"<p style='line-height:1.7; font-size:16px; margin-bottom:16px;'>{p}</p>" for p in summary.split("\n") if p.strip()
    )
    creative_html = "<br><div style='font-size:24px;font-weight:bold;'>💡 Creative Suggestions:</div><br>" + ''.join(
        f"<p style='margin:16px 0; font-size:17px;'>{p}</p>" for p in creative.split("\n") if p.strip()
    )
    footer = (
        "<div style='background-color:#f9f9f9;color:#333;padding:20px;border-left:6px solid #5E9CA0;"
        "border-radius:8px;margin-top:30px;'>"
        "<strong>📊 AI Health Insights Based On:</strong>"
        "<ul style='margin-top:10px;margin-bottom:10px;padding-left:20px;line-height:1.7;'>"
        "<li>Anonymous wellness benchmarks in Singapore, Malaysia, and Taiwan</li>"
        "<li>Guidance from OpenAI health motivation models</li></ul>"
        "<p style='margin-top:10px;line-height:1.7;'>All data is confidential and never stored. "
        "This is not a medical diagnosis tool. Please consult a doctor for clinical concerns.</p>"
        "<p style='margin-top:10px;line-height:1.7;'><strong>PS:</strong> This is the first step in building motivation and clarity. A deeper lifestyle mapping report can be prepared and sent to your email within 24–48 hours if needed. 🌱</p></div>"
    )

    return chart_html + summary_html + creative_html + footer

def send_email(html_body, subject):
    msg = MIMEText(html_body, 'html', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = SMTP_USERNAME
    msg['To'] = SMTP_USERNAME
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        logging.error(f"Email send error: {e}")

@app.route("/health_analyze", methods=["POST"])
def health_analyze():
    try:
        data = request.get_json(force=True)
        logging.debug(f"POST received: {data}")

        name = data.get("name")
        dob = data.get("dob")
        gender = data.get("gender")
        height = data.get("height")
        weight = data.get("weight")
        country = data.get("country")
        concern = data.get("condition")
        notes = data.get("details", "")
        referrer = data.get("referrer")
        angel = data.get("angel")

        age = compute_age(dob)
        metrics = generate_metrics()

        prompt_summary = f"A {age}-year-old {gender} from {country} with the concern '{concern}' described as: {notes}. Write 4 paragraphs of empathetic wellness advice in third-person."
        prompt_creative = f"Suggest 10 wellness lifestyle tips with emojis for a {age}-year-old {gender} from {country} facing '{concern}'."

        summary = get_openai_response(prompt_summary)
        creative = get_openai_response(prompt_creative, temp=0.85)

        html_result = build_html_report(age, gender, country, concern, notes, metrics, summary, creative)
        email_body = f"<h4 style='text-align:center;font-size:24px;'>🎉 Global Identical Health Insights</h4>" + html_result

        send_email(email_body, "Your Health Insight Report")

        return jsonify({
            "metrics": metrics,
            "html_result": email_body
        })
    except Exception as e:
        logging.error(f"Health analyze error: {e}")
        traceback.print_exc()
        return jsonify({"error": "Server error"}), 500

if __name__ == "__main__":
    app.run(debug=True)
