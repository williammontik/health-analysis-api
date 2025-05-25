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
            f"🧠 Summary:\n{age}-year-old {gender} from {country} is facing '{concern}'. Additional details: {notes}.\n"
            f"Please write 4 factual and relevant insights in paragraph form using third person tone (avoid 'you'). "
            f"Use global statistics, regional trends and clear outcomes if possible.",
        "creative": lambda age, gender, country, concern, notes:
            f"💡 Creative Suggestions:\nSuggest 10 creative and evidence-based health tips for a {age}-year-old {gender} in {country} with '{concern}'. "
            f"Use emoji + brief explanation, e.g. '🥗 Eat broccoli — reduces inflammation'.",
        "charts": lambda age, gender, country, concern, notes:
            f"A {age}-year-old {gender} from {country} is experiencing '{concern}'. Notes: {notes}. "
            f"Create 3 health-related chart categories (start each with ###). Under each, list 3 unique indicators with varying values (25–90%), format: Label: Value%."
    },
    "zh": {
        "summary": lambda age, gender, country, concern, notes:
            f"🧠 总结：\n一位{age}岁的{gender}来自{country}，健康问题是“{concern}”。补充说明：{notes}。\n"
            f"请用第三人称写出4段简明分析内容，引用全球趋势或相关统计，避免使用“你”。",
        "creative": lambda age, gender, country, concern, notes:
            f"💡 创意建议：\n请列出10个简洁有趣的健康建议，适用于{country}一位{age}岁的{gender}（问题：{concern}）。"
            f"用emoji和简短解释，例如：🥗 吃西兰花—减缓炎症。",
        "charts": lambda age, gender, country, concern, notes:
            f"一位{age}岁的{gender}来自{country}，健康问题为“{concern}”。补充：{notes}。\n"
            f"请以 ### 开头列出3个图表分类，每类下列出3项不同健康指标，格式为「名称: 数值%」（25–90%之间，避免重复）。"
    },
    "tw": {
        "summary": lambda age, gender, country, concern, notes:
            f"🧠 摘要：\n這位{age}歲的{gender}來自{country}，主要問題是「{concern}」。補充：{notes}。\n"
            f"請以第三人稱寫出4段健康分析（避免用“你”），參考趨勢與研究。",
        "creative": lambda age, gender, country, concern, notes:
            f"💡 創意建議：\n請為{country}一位{age}歲的{gender}（問題：「{concern}」）提供10項健康習慣建議。"
            f"每條用emoji和簡要說明，例如：🍅 吃番茄—補充茄紅素。",
        "charts": lambda age, gender, country, concern, notes:
            f"這位{age}歲的{gender}來自{country}，健康問題為「{concern}」。補充：{notes}。\n"
            f"請列出3個圖表分類（以 ### 開頭），每類含3個具體指標，格式為「名稱: 數值%」，數值介於25–90%之間，避免重複。"
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
        res = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=temp
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"OpenAI response error: {e}")
        return "⚠️ 無法生成內容"

def generate_chart_metrics(prompt):
    try:
        res = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8
        )
        lines = res.choices[0].message.content.strip().split("\n")
        metrics, title, labels, values = [], "", [], []
        for line in lines:
            if line.startswith("###"):
                if title and labels and values:
                    metrics.append({"title": title, "labels": labels, "values": values})
                title = line[3:].strip()
                labels, values = [], []
            elif ":" in line:
                parts = line.split(":", 1)
                try:
                    labels.append(parts[0].strip("-• ").strip())
                    values.append(int(parts[1].strip().replace("%", "")))
                except:
                    continue
        if title and labels and values:
            metrics.append({"title": title, "labels": labels, "values": values})
        return metrics
    except Exception as e:
        logging.warning(f"GPT chart error: {e}")
        return [{"title": "General Health", "labels": ["A", "B", "C"], "values": [60, 70, 80]}]

def send_email(html, lang):
    subject = LANGUAGE.get(lang, LANGUAGE["en"])["email_subject"]
    msg = MIMEText(html, "html", "utf-8")
    msg['Subject'] = subject
    msg['From'] = SMTP_USERNAME
    msg['To'] = SMTP_USERNAME
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
            s.starttls()
            s.login(SMTP_USERNAME, SMTP_PASSWORD)
            s.send_message(msg)
    except Exception as e:
        logging.error(f"Email error: {e}")

@app.route("/health_analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json()
        lang = data.get("lang", "en").strip()
        if lang not in PROMPTS:
            lang = "en"

        name = data.get("name")
        dob = data.get("dob")
        gender = data.get("gender")
        height = data.get("height")
        weight = data.get("weight")
        country = data.get("country")
        concern = data.get("condition")
        notes = data.get("details") or "無補充說明"
        ref = data.get("referrer")
        angel = data.get("angel")
        age = compute_age(dob)

        summary = get_openai_response(PROMPTS[lang]["summary"](age, gender, country, concern, notes))
        creative = get_openai_response(PROMPTS[lang]["creative"](age, gender, country, concern, notes), temp=0.85)
        metrics = generate_chart_metrics(PROMPTS[lang]["charts"](age, gender, country, concern, notes))

        chart_html = ""
        for m in metrics:
            chart_html += f"<strong>{m['title']}</strong><br>"
            for lbl, val in zip(m['labels'], m['values']):
                chart_html += (
                    f"<div style='display:flex;margin:8px 0;align-items:center;'>"
                    f"<span style='width:180px'>{lbl}</span>"
                    f"<div style='flex:1;background:#eee;border-radius:6px;overflow:hidden;'>"
                    f"<div style='width:{val}%;height:14px;background:#5E9CA0'></div></div>"
                    f"<span style='margin-left:10px;'>{val}%</span></div>"
                )
            chart_html += "<br>"

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
            f"{chart_html}<br>"
            f"<div style='white-space:pre-wrap;font-size:16px;'>{summary}</div><br>"
            f"<div style='white-space:pre-wrap;font-size:16px;'>{creative}</div><br>"
            f"<p style='color:#888;'>🛡️ Disclaimer:<br>🩺 This platform offers general lifestyle suggestions. "
            f"Please consult a licensed medical professional for diagnosis or treatment decisions.</p>"
        )

        send_email(html, lang)

        return jsonify({
            "metrics": metrics,
            "analysis": summary,
            "creative": creative,
            "footer": "🩺 本平台提供一般健康建議，如有需要請諮詢專業醫生。"
        })

    except Exception as e:
        logging.error(f"Analyze error: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 5000)), host="0.0.0.0")
