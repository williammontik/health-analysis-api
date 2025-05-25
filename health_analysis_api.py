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
    "en": {"email_subject": "Your Health Insight Report", "report_title": "🎉 Global Health Insights"},
    "zh": {"email_subject": "您的健康深度抽象", "report_title": "🎉 全球健康深度抽象"},
    "tw": {"email_subject": "您的健康深度揭示", "report_title": "🎉 全球健康深度揭示"}
}

PROMPTS = {
    "en": {
        "summary": lambda age, gender, country, concern, notes:
            f"🧠 Summary:\n{age}-year-old {gender} from {country} is facing '{concern}'. Additional details: {notes}.\n"
            f"Please write 4 factual and relevant insights in paragraph form using third person tone (avoid 'you').\n"
            f"Use global statistics, regional trends and clear outcomes if possible.",

        "creative": lambda age, gender, country, concern, notes:
            f"💡 Creative Suggestions:\nPlease suggest 10 creative health habits for a {age}-year-old {gender} from {country} with '{concern}'. "
            f"Include emojis and brief explanations (e.g., '🥗 Eat broccoli — reduces inflammation'). Keep each idea short and focused on lifestyle."
    },
    "zh": {
        "summary": lambda age, gender, country, concern, notes:
            f"🧠 总结：\n一位{age}岁的{gender}来自{country}，主要健康问题为“{concern}”。补充说明：{notes}。\n"
            f"请以第三人称的方式编写4段简洁明了的分析内容，引用全球趋势或相关统计，避免使用“你”。",

        "creative": lambda age, gender, country, concern, notes:
            f"💡 创意建议：\n请列出10个简洁有趣的健康生活习惯建议，适用于{country}一位{age}岁的{gender}，健康问题为“{concern}”。"
            f"每项建议加上Emoji和简短说明（例如：🥗 吃西兰花－－有助于减缓炎症）。"
    },
    "tw": {
        "summary": lambda age, gender, country, concern, notes:
            f"🧠 摘要：\n這位{age}歲的{gender}來自{country}，健康困擾為「{concern}」。補充說明：{notes}。\n"
            f"請用第三人稱編寫4段分析建議，包含真實資訊、趨勢與建議（請避免使用「你」）。",

        "creative": lambda age, gender, country, concern, notes:
            f"💡 創意建議：\n請提出10項實用、生活化的健康改善建議，適用於{country}一位{age}歲的{gender}，主要問題為「{concern}」。"
            f"每項建議使用emoji和簡潔說明（例如：🍕 吃番茄－－有助於攞取茶紅素）。"
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
        notes = data.get("details", "") or "無补充說明"
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
            f"<div style='white-space:pre-wrap; font-size:16px;'>{summary_text}</div><br>"
            f"<div style='white-space:pre-wrap; font-size:16px;'><h4 style='font-size:24px;'>💡 Creative Suggestions:</h4>"
            f"<div style='margin-top:10px;'>{creative_text.replace('\n', '<br><br>')}</div></div><br>"
            f"<p style='color:#888;'>🛡️ Disclaimer:<br>🧪 This platform offers general lifestyle suggestions. Please consult a licensed medical professional for diagnosis or treatment decisions.</p>"
        )

        send_email(html, lang)

        return jsonify({
            "analysis": summary_text,
            "creative": f"\n\n{creative_text}",
            "footer": "🧪 This report is for general informational purposes only. Please consult a medical professional."
        })

    except Exception as e:
        logging.error(f"health_analyze error: {e}")
        return jsonify({"error": "server error"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 5000)), host="0.0.0.0")
