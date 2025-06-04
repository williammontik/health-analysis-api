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

LANGUAGE = {
    "en": {
        "email_subject": "Your Health Insight Report",
        "report_title": "🎉 Global Identical Health Insights"
    }
}

LANGUAGE_TEXTS = {
    "en": {
        "name": "Full Name", "dob": "Date of Birth", "country": "Country", "gender": "Gender",
        "age": "Age", "height": "Height (cm)", "weight": "Weight (kg)", "concern": "Main Concern",
        "desc": "Description", "ref": "Referrer", "angel": "Caring Person"
    }
}

def generate_chart_prompt():
    return (
        "Generate exactly 3 distinct health categories. "
        "Use headers starting with ### (e.g., ### Dermatological Health). "
        "Each category must contain exactly 2 unique health metrics in the format 'Label: 60%'. "
        "The total output must include 3 category titles and 6 different metrics. "
        "Use realistic values between 25%–90%. Format strictly and clearly."
    )

def send_email(to_address, subject, body):
    msg = MIMEText(body, "html")
    msg["Subject"] = subject
    msg["From"] = SMTP_USERNAME
    msg["To"] = to_address

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        logging.error(f"Email sending failed: {e}")
        return False

@app.route("/health_analyze", methods=["POST"])
def analyze_health():
    try:
        data = request.json
        lang = data.get("lang", "en")
        user_info = {
            "name": data.get("name"),
            "dob": data.get("dob"),
            "gender": data.get("gender"),
            "country": data.get("country"),
            "height": data.get("height"),
            "weight": data.get("weight"),
            "concern": data.get("concern"),
            "desc": data.get("desc"),
            "ref": data.get("ref"),
            "angel": data.get("angel"),
            "email": data.get("email")
        }

        age = calculate_age(data.get("dob"))
        user_info["age"] = age

        chart_prompt = generate_chart_prompt()
        chart_response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": chart_prompt}]
        ).choices[0].message.content.strip()

        summary_prompt = (
            f"Based on the following health data and user profile, write a warm, emotionally supportive, "
            f"and medically informed summary in 3 to 4 detailed paragraphs.\n\n"
            f"User info:\n- Gender: {user_info['gender']}\n- Age: {user_info['age']}\n"
            f"- Country: {user_info['country']}\n- Main concern: {user_info['concern']}\n\n"
            f"Chart data:\n{chart_response}\n\n"
            f"Rules: DO NOT mention the person's name. DO NOT say 'as a wellness coach' or 'this 53-year-old man...'. "
            f"Instead, use phrases like 'individuals in this age group across Malaysia' or 'men in their 50s'. "
            f"The tone should be insightful, regional, and emotionally rich. Close with gentle suggestions."
        )

        summary_response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": summary_prompt}]
        ).choices[0].message.content.strip()

        report_title = LANGUAGE[lang]["report_title"]
        full_output = f"<h2>{report_title}</h2><pre>{chart_response}</pre><p>{summary_response}</p>"

        send_email(user_info["email"], LANGUAGE[lang]["email_subject"], full_output)

        return jsonify({"status": "success", "title": report_title, "chart": chart_response, "summary": summary_response})

    except Exception as e:
        logging.error(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500

def calculate_age(dob_str):
    try:
        birth_date = parser.parse(dob_str)
        today = datetime.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    except:
        return None
