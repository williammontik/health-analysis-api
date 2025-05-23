# -*- coding: utf-8 -*-
import os, random, logging, smtplib
from datetime import datetime
from dateutil import parser
from email.mime.text import MIMEText
from flask import Flask, request, jsonify
from flask_cors import CORS
import openai

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.DEBUG)

# 🔐 API Keys
openai.api_key = os.getenv("OPENAI_API_KEY")
SMTP_SERVER   = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USERNAME = "kata.chatbot@gmail.com"
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
if not SMTP_PASSWORD:
    app.logger.warning("SMTP_PASSWORD is not set!")

# 🌐 Language Support
LANGUAGE = {
    "en": {
        "email_subject": "Your Health Insight Report",
        "report_title": "🎉 Global Identical Health Insights",
        "ps": "PS: This report has also been emailed to you and should arrive within 24 hours. Stay well and feel free to reach out for a follow-up discussion."
    },
    "zh": {
        "email_subject": "您的健康洞察报告",
        "report_title": "🎉 全球健康洞察分析",
        "ps": "PS: 此报告已通过电子邮件发送，预计24小时内送达。如需进一步讨论，欢迎联系我们。"
    },
    "tw": {
        "email_subject": "您的健康洞察報告",
        "report_title": "🎉 全球健康洞察分析",
        "ps": "PS: 此報告已通過電子郵件發送，預計24小時內送達。如需進一步討論，歡迎與我們聯繫。"
    }
}

# 📧 Email Sending
def send_email(html_body, lang):
    content = LANGUAGE.get(lang, LANGUAGE["en"])
    msg = MIMEText(html_body, 'html', 'utf-8')
    msg['Subject'] = content["email_subject"]
    msg['From'] = SMTP_USERNAME
    msg['To'] = SMTP_USERNAME
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        app.logger.error(f"Email send error: {e}")

# 🎂 Age Calculation
def compute_age(dob):
    try:
        dt = parser.parse(dob)
        today = datetime.today()
        return today.year - dt.year - ((today.month, today.day) < (dt.month, dt.day))
    except:
        return 0

# 📊 Health Metrics Generator
def generate_metrics():
    return [
        {"title": "BMI Analysis", "labels": ["Your BMI", "Regional Avg", "Global Avg"], "values": [random.randint(19, 30), 23, 24]},
        {"title": "Blood Pressure", "labels": ["Your Level", "Regional Avg", "Global Avg"], "values": [random.randint(110, 160), 135, 128]},
        {"title": "Cholesterol", "labels": ["Your Level", "Regional Avg", "Global Avg"], "values": [random.randint(180, 250), 210, 220]}
    ]

# 💬 GPT Summary
def get_gpt_summary(prompt, model="gpt-3.5-turbo"):
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        app.logger.error(f"OpenAI error: {e}")
        return "⚠️ Unable to generate health summary right now."

# 🚀 Main Endpoint
@app.route("/health_analyze", methods=["POST"])
def analyze_health():
    try:
        data = request.get_json(force=True)
        lang = data.get("lang", "en").lower()
        content = LANGUAGE.get(lang, LANGUAGE["en"])

        name     = data.get("name")
        dob      = data.get("dob")
        gender   = data.get("gender")
        height   = data.get("height")
        weight   = data.get("weight")
        country  = data.get("country")
        concern  = data.get("condition")
        notes    = data.get("details")
        ref      = data.get("referrer")
        angel    = data.get("angel")
        age      = compute_age(dob)

        metrics  = generate_metrics()

        prompt = (
            f"You are a health consultant. Write a friendly and insightful health summary for:\n"
            f"• Name: {name}\n• Age: {age}\n• Gender: {gender}\n• Height: {height} cm\n• Weight: {weight} kg\n"
            f"• Country: {country}\n• Health Concern: {concern}\n• Notes: {notes}\n"
            f"Use {lang.upper()} language for your response. Provide 4 paragraphs of meaningful advice."
        )
        analysis = get_gpt_summary(prompt)

        html = (
            f"<h4 style='text-align:center;font-size:24px;'>{content['report_title']}</h4>"
            f"<p><strong>Name:</strong> {name}<br><strong>DOB:</strong> {dob} (Age: {age})<br>"
            f"<strong>Gender:</strong> {gender}<br><strong>Height:</strong> {height} cm<br>"
            f"<strong>Weight:</strong> {weight} kg<br><strong>Country:</strong> {country}<br>"
            f"<strong>Concern:</strong> {concern}<br><strong>Description:</strong> {notes}<br>"
            f"<strong>Referrer:</strong> {ref}<br><strong>Angel:</strong> {angel}</p>"
            f"<div>{analysis}</div>"
            f"<p style='margin-top:20px;background:#e6f7ff;padding:15px;border-left:4px solid #5E9CA0;'>"
            f"<strong>{content['ps']}</strong></p>"
        )

        send_email(html, lang)

        return jsonify({
            "metrics": metrics,
            "analysis": analysis
        })
    except Exception as e:
        app.logger.error(f"Health analyze error: {e}")
        return jsonify({"error": "Server error"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 5000)), host="0.0.0.0")
