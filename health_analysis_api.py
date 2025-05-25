
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
    "zh": {"email_subject": "您的健康洞察报告", "report_title": "🎉 全球健康洞察"},
    "tw": {"email_subject": "您的健康洞察報告", "report_title": "🎉 全球健康洞察"}
}

PROMPTS = {
    "en": {
        "summary": lambda age, gender, country, concern, notes:
            f"{age}-year-old {gender} from {country} is facing '{concern}'. Additional details: {notes}.
"
            f"Please write 4 factual and relevant insights in paragraph form using third person tone (avoid 'you').
"
            f"Use global statistics, regional trends and clear outcomes if possible.",
        "creative": lambda age, gender, country, concern, notes:
            f"Please suggest 10 creative health habits for a {age}-year-old {gender} from {country} with '{concern}'. "
            f"Include emojis and brief explanations (e.g., '🥗 Eat broccoli — reduces inflammation'). Keep each idea short and focused on lifestyle."
    },
    "zh": {
        "summary": lambda age, gender, country, concern, notes:
            f"一位{age}岁的{gender}来自{country}，主要健康问题为“{concern}”。补充说明：{notes}。
"
            f"请以第三人称的方式撰写4段简洁明了的分析内容，引用全球趋势或相关统计，避免使用“你”。",
        "creative": lambda age, gender, country, concern, notes:
            f"请列出10个简洁有趣的健康生活习惯建议，适用于{country}一位{age}岁的{gender}，健康问题为“{concern}”。"
            f"每项建议加上Emoji和简短说明（例如：🥗 吃西兰花——有助于减缓炎症）。"
    },
    "tw": {
        "summary": lambda age, gender, country, concern, notes:
            f"這位{age}歲的{gender}來自{country}，健康困擾為「{concern}」。補充說明：{notes}。
"
            f"請用第三人稱撰寫4段分析建議，包含真實資訊、趨勢與建議（請避免使用「你」）。",
        "creative": lambda age, gender, country, concern, notes:
            f"請提出10項實用、生活化的健康改善建議，適用於{country}一位{age}歲的{gender}，主要問題為「{concern}」。"
            f"每項建議使用emoji和簡潔說明（例如：🍅 吃番茄——有助於攝取茄紅素）。"
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
        notes = data.get("details", "") or "無補充說明"
        ref = data.get("referrer")
        angel = data.get("angel")
        age = compute_age(dob)

        summary_text = get_openai_response(PROMPTS[lang]["summary"](age, gender, country, concern, notes))
        creative_text = get_openai_response(PROMPTS[lang]["creative"](age, gender, country, concern, notes), temp=0.9)

        # Format creative suggestions with title and spacing
        formatted_creative = (
            "<h3 style='font-size:24px;'>💡 Creative Suggestions:</h3><br>" +
            "".join(f"<p style='margin-bottom:10px;'>{line.strip()}</p>" for line in creative_text.split("\n") if line.strip())
        )

        # Format summary as paragraphs
        formatted_summary = (
            "<div style='font-size:16px; white-space:pre-wrap;'><strong>🧠 Summary:</strong><br><p style='margin-bottom:10px;'>"
            + "</p><p style='margin-bottom:10px;'>".join(summary_text.split("\n")) + "</p></div>"
        )

        # Disclaimers by language
        disclaimers = {
            "en": "🛡️ Disclaimer:<br>🩺 This platform offers general lifestyle suggestions. Please consult a licensed medical professional for diagnosis or treatment decisions.",
            "zh": "🛡️ 免责声明：<br>🩺 本平台提供一般健康建议，如有需要请咨询专业医生。",
            "tw": "🛡️ 免責聲明：<br>🩺 本平台提供一般健康建議，如有需要請諮詢專業醫生。"
        }

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
            f"{formatted_summary}<br>{formatted_creative}<br>"
            f"<p style='color:#888;'>{disclaimers[lang]}</p>"
        )

        send_email(html, lang)

        return jsonify({
            "analysis": formatted_summary,
            "creative": formatted_creative,
            "footer": f"<p style='color:#888;'>{disclaimers[lang]}</p>"
        })

    except Exception as e:
        logging.error(f"health_analyze error: {e}")
        return jsonify({"error": "server error"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 5000)), host="0.0.0.0")
