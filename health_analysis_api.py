# -*- coding: utf-8 -*-
import os, logging, smtplib, random
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
        "report_title": "🎉 Global Identical Health Insights",
        "disclaimer": "🩺 This platform offers general lifestyle suggestions. Please consult a licensed medical professional for diagnosis or treatment decisions.",
        "creative_title": "💡 Creative Health Suggestions"
    },
    "zh": {
        "email_subject": "您的健康洞察報告",
        "report_title": "🎉 全球健康洞察（简体）",
        "disclaimer": "🩺 本平台仅提供一般生活建议。如有诊断或治疗需求，请咨询专业医生。",
        "creative_title": "💡 创意健康建议"
    },
    "tw": {
        "email_subject": "您的健康洞察報告",
        "report_title": "🎉 全球健康洞察（繁體）",
        "disclaimer": "🩺 本平台僅提供一般生活建議。如需診療請諮詢合格醫師。",
        "creative_title": "💡 創意健康建議"
    }
}

# Utility Functions

def build_messages(lang, user_prompt):
    system_msg = {
        "en": "Please respond entirely in English.",
        "zh": "请确保以下所有回答都使用简体中文，不要使用英文。",
        "tw": "請確保以下所有回答都使用繁體中文，請勿使用英文。"
    }.get(lang, "Please respond in English.")

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_prompt}
    ]

def send_email(html_body, lang):
    subject = LANGUAGE.get(lang, LANGUAGE["en"])["email_subject"]
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
        app.logger.error(f"Email send error: {e}")

def compute_age(dob):
    try:
        dt = parser.parse(dob)
        today = datetime.today()
        return today.year - dt.year - ((today.month, today.day) < (dt.month, dt.day))
    except:
        return 0

def get_openai_response(prompt, lang, temp=0.7):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=build_messages(lang, prompt),
            temperature=temp
        )
        return response.choices[0].message.content
    except Exception as e:
        app.logger.error(f"OpenAI error: {e}")
        return "⚠️ Unable to generate content."

def generate_metrics_with_ai(prompt_text, lang):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=build_messages(lang, prompt_text),
            temperature=0.7
        )
        lines = response.choices[0].message.content.strip().split("\n")
        metrics = []
        current_title = ""
        labels = []
        values = []
        for line in lines:
            if line.startswith("###"):
                if current_title and labels and values:
                    metrics.append({
                        "title": current_title,
                        "labels": labels,
                        "values": values
                    })
                current_title = line[3:].strip()
                labels, values = [], []
            elif ":" in line:
                label, val = line.split(":", 1)
                labels.append(label.strip())
                try:
                    values.append(int(val.strip().replace("%", "")))
                except:
                    values.append(50)
        if current_title and labels and values:
            metrics.append({"title": current_title, "labels": labels, "values": values})
        if not metrics:
            raise ValueError("GPT returned no metrics.")
        return metrics
    except Exception as e:
        logging.warning(f"GPT metric error: {e}")
        return []

# Route
@app.route("/health_analyze", methods=["POST"])
def health_analyze():
    try:
        data = request.get_json(force=True)
        logging.debug(f"📥 Incoming request: {data}")

        lang = data.get("lang", "en").strip()
        content = LANGUAGE.get(lang, LANGUAGE["en"])

        name     = data.get("name")
        dob      = data.get("dob")
        gender   = data.get("gender")
        height   = data.get("height")
        weight   = data.get("weight")
        country  = data.get("country")
        concern  = data.get("condition")
        notes    = data.get("details", "") or "No additional description provided."
        ref      = data.get("referrer")
        angel    = data.get("angel")
        age      = compute_age(dob)

        if lang not in LANGUAGE:
            lang = "en"

        # Prompt setup
        summary_prompt = PROMPTS[lang]["summary"](age, gender, country, concern, notes)
        creative_prompt = PROMPTS[lang]["creative"](age, gender, country, concern, notes)
        chart_prompt = chart_prompts[lang](age, gender, country, concern, notes)

        # Generate
        metrics = generate_metrics_with_ai(chart_prompt, lang)
        summary = get_openai_response(summary_prompt, lang)
        creative = get_openai_response(creative_prompt, lang, temp=0.85)

        # Assemble chart
        chart_html = ""
        for metric in metrics:
            chart_html += f"<strong>{metric['title']}</strong><br>"
            for label, value in zip(metric['labels'], metric['values']):
                chart_html += (
                    f"<div style='display:flex; align-items:center; margin-bottom:8px;'>"
                    f"<span style='width:180px;'>{label}</span>"
                    f"<div style='flex:1; background:#eee; border-radius:5px; overflow:hidden;'>"
                    f"<div style='width:{value}%; height:14px; background:#5E9CA0;'></div>"
                    f"</div><span style='margin-left:10px;'>{value}%</span></div>"
                )
            chart_html += "<br>"

        creative_html = f"<br><br><h3 style='font-size:24px; font-weight:bold;'>{content['creative_title']}</h3><br>"
        creative_html += "".join(
            f"<p style='margin-bottom:14px;'>{line.strip()}</p>"
            for line in creative.split("\n") if line.strip()
        )

        footer = f"<p style='color:#888;'>{content['disclaimer']}</p>"

        html = (
            f"<h4 style='text-align:center; font-size:24px;'>{content['report_title']}</h4>"
            f"<p><strong>Legal Name:</strong> {name}<br><strong>Date of Birth:</strong> {dob}<br>"
            f"<strong>Country:</strong> {country}<br><strong>Gender:</strong> {gender}<br><strong>Age:</strong> {age}<br>"
            f"<strong>Height:</strong> {height} cm<br><strong>Weight:</strong> {weight} kg<br>"
            f"<strong>Main Concern:</strong> {concern}<br><strong>Brief Description:</strong> {notes}<br>"
            f"<strong>Referrer:</strong> {ref}<br><strong>Angel:</strong> {angel}</p>"
            f"{chart_html}"
            f"<div>{summary}</div>"
            f"{creative_html}"
            f"{footer}"
        )

        send_email(html, lang)

        return jsonify({
            "metrics": metrics,
            "analysis": summary,
            "creative": creative_html,
            "footer": footer
        })

    except Exception as e:
        app.logger.error(f"❌ Health analyze error: {e}")
        return jsonify({"error": "Server error"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 5000)), host="0.0.0.0")
