# -*- coding: utf-8 -*-
import os, logging, smtplib
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
    "en": {"email_subject": "Your Health Insight Report", "report_title": "\ud83c\udf89 Global Health Insights"},
    "zh": {"email_subject": "\u60a8\u7684\u5065\u5eb7\u6d4b\u8bd5\u62a5\u544a", "report_title": "\ud83c\udf89 \u5168\u7403\u5065\u5eb7\u6d4b\u8bd5"},
    "tw": {"email_subject": "\u60a8\u7684\u5065\u5eb7\u6aa2\u6e2c\u5831\u544a", "report_title": "\ud83c\udf89 \u5168\u7403\u5065\u5eb7\u6aa2\u6e2c"}
}

PROMPTS = {
    "en": {
        "summary": lambda age, gender, country, concern, notes:
            f"\ud83e\uddd0 Summary:\n{age}-year-old {gender} from {country} is facing '{concern}'. Additional details: {notes}.\n"
            "Please write 4 factual and relevant insights in paragraph form using third person tone (avoid 'you').\n"
            "Use global statistics, regional trends and clear outcomes if possible.",

        "creative": lambda age, gender, country, concern, notes:
            f"\ud83d\udca1 Creative Suggestions:\nPlease suggest 10 creative health habits for a {age}-year-old {gender} from {country} with '{concern}'. "
            "Include emojis and brief explanations (e.g., '\ud83e\udd57 Eat broccoli \u2014 reduces inflammation'). Keep each idea short and focused on lifestyle."
    },
    "zh": {
        "summary": lambda age, gender, country, concern, notes:
            f"\ud83e\uddd0 \u603b\u7ed3:\n\u4e00\u4f4d{age}\u5c81\u7684{gender}\u6765\u81ea{country}\uff0c\u4e3b\u8981\u5065\u5eb7\u95ee\u9898\u4e3a\u201c{concern}\u201d\u3002\u8865\u5145\u8bf4\u660e\uff1a{notes}\u3002\n"
            "\u8bf7\u4ee5\u7b2c\u4e09\u4eba\u79f0\u7684\u65b9\u5f0f\u6328\u51994\u6bb5\u7b80\u6d01\u660e\u4e86\u7684\u5206\u6790\u5185\u5bb9\uff0c\u5f15\u7528\u5168\u7403\u8d8b\u52bf\u6216\u76f8\u5173\u7edf\u8ba1\uff0c\u907f\u514d\u4f7f\u7528\u201c\u4f60\u201d\u3002",

        "creative": lambda age, gender, country, concern, notes:
            f"\ud83d\udca1 \u521b\u610f\u5efa\u8bae:\n\u8bf7\u5217\u51fa10\u4e2a\u7b80\u6d01\u6709\u8da3\u7684\u5065\u5eb7\u751f\u6d3b\u4e60\u60ef\u5efa\u8bae\uff0c\u9002\u7528\u4e8e{country}\u4e00\u4f4d{age}\u5c81\u7684{gender}\uff0c\u5065\u5eb7\u95ee\u9898\u4e3a\u201c{concern}\u201d\u3002"
            "\u6bcf\u9879\u5efa\u8bae\u52a0\u4e0aEmoji\u548c\u7b80\u77ed\u8bf4\u660e\uff08\u4f8b\u5982\uff1a\ud83e\udd57 \u5403\u897f\u5170\u82b1\u2014\u6709\u52a9\u4e8e\u51cf\u7f13\u708e\u75c7\uff09\u3002"
    },
    "tw": {
        "summary": lambda age, gender, country, concern, notes:
            f"\ud83e\uddd0 \u6458\u8981:\n\u9019\u4f4d{age}\u6b72\u7684{gender}\u4f86\u81ea{country}\uff0c\u5065\u5eb7\u56f0\u64fe\u70ba\u300c{concern}\u300d\u3002\u88dc\u5145\u8aaa\u660e\uff1a{notes}\u3002\n"
            "\u8acb\u7528\u7b2c\u4e09\u4eba\u7a31\u64da\u64ec\u5beb4\u6bb5\u5206\u6790\u5efa\u8b70\uff0c\u5305\u542b\u771f\u5be6\u8cc7\u8a0a\u3001\u8da8\u52e2\u8207\u5efa\u8b70\uff08\u8acb\u907f\u514d\u4f7f\u7528\u300c\u4f60\u300d\uff09\u3002",

        "creative": lambda age, gender, country, concern, notes:
            f"\ud83d\udca1 \u5275\u610f\u5efa\u8b70:\n\u8acb\u63d010\u9805\u5be6\u7528\u3001\u751f\u6d3b\u5316\u7684\u5065\u5eb7\u6539\u5584\u5efa\u8b70\uff0c\u9069\u7528\u65bc{country}\u4e00\u4f4d{age}\u6b72\u7684{gender}\uff0c\u4e3b\u8981\u554f\u984c\u70ba\u300c{concern}\u300d\u3002"
            "\u6bcf\u9805\u5efa\u8b70\u4f7f\u7528emoji\u548c\u7c21\u6f54\u8aaa\u660e\uff08\u4f8b\u5982\uff1a\ud83c\udf45 \u5403\u756a\u8304\u2014\u6709\u52a9\u65bc\u6446\u812b\u8309\u9eb5\u7d20\uff09\u3002"
    }
}

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
        return "⚠️ 無法生成內容"

def send_email(html_body, lang):
    subject = LANGUAGE.get(lang, LANGUAGE["en"])['email_subject']
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
        lang = data.get("lang", "en").strip()
        if lang not in LANGUAGE:
            lang = "en"

        name = data.get("name")
        dob = data.get("dob")
        gender = data.get("gender")
        height = data.get("height")
        weight = data.get("weight")
        country = data.get("country")
        concern = data.get("condition")
        notes = data.get("details", "") or "無補充說明"
        ref = data.get("referrer")
        angel = data.get("angel")
        age = compute_age(dob)

        summary_text = get_openai_response(PROMPTS[lang]["summary"](age, gender, country, concern, notes))
        creative_text = get_openai_response(PROMPTS[lang]["creative"](age, gender, country, concern, notes), temp=0.9)

        html = (
            f"<h4 style='text-align:center;font-size:24px;'>{LANGUAGE[lang]['report_title']}</h4><br>"
            f"<strong>👤 Name:</strong> {name}<br>"
            f"<strong>🗓️ DOB:</strong> {dob}<br>"
            f"<strong>🌍 Country:</strong> {country}<br>"
            f"<strong>⚧️ Gender:</strong> {gender}<br>"
            f"<strong>🎂 Age:</strong> {age}<br>"
            f"<strong>📏 Height:</strong> {height} cm<br>"
            f"<strong>⚖️ Weight:</strong> {weight} kg<br>"
            f"<strong>📌 Concern:</strong> {concern}<br>"
            f"<strong>📝 Notes:</strong> {notes}<br>"
            f"<strong>💬 Referrer:</strong> {ref}<br>"
            f"<strong>👼 Angel:</strong> {angel}<br><br>"
            + "<div style='white-space:pre-wrap; font-size:16px;'>" + summary_text + "</div><br>"
            + "<h3 style='font-size:24px;'>💡 Creative Suggestions:</h3><br>"
            + "<div style='white-space:pre-wrap; font-size:16px; line-height:1.8;'>" + creative_text + "</div><br>"
            + "<p style='color:#888;'>🛡️ Disclaimer:<br>🩺 This platform offers general lifestyle suggestions. Please consult a licensed medical professional for diagnosis or treatment decisions.</p>"
        )

        send_email(html, lang)

        return jsonify({
            "analysis": summary_text,
            "creative": creative_text,
            "footer": "🩺 此報告僅供參考用途。如有健康疑慮，請諮詢專業醫療人員。"
        })

    except Exception as e:
        logging.error(f"health_analyze error: {e}")
        return jsonify({"error": "server error"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 5000)), host="0.0.0.0")
