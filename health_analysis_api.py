# -*- coding: utf-8 -*-
import os, logging, smtplib, traceback, re
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
    "en": {"email_subject": "Your Health Insight Report", "report_title": "🎉 Global Identical Health Insights"},
    "zh": {"email_subject": "您的健康洞察报告", "report_title": "🎉 全球健康洞察（简体）"},
    "tw": {"email_subject": "您的健康洞察報告", "report_title": "🎉 全球健康洞察（繁體）"}
}

LANGUAGE_TEXTS = {
    "en": {
        "name": "Given Legal Name", "dob": "Date of Birth", "country": "Country", "gender": "Gender",
        "age": "Age", "height": "Height (cm)", "weight": "Weight (kg)", "concern": "Main Concern",
        "desc": "Brief Description", "ref": "Referrer", "angel": "Caring Person",
        "footer": "📩 This report has been emailed to you. All content is generated by KataChat AI, PDPA-compliant."
    },
    "zh": {
        "name": "法定姓名", "dob": "出生日期", "country": "国家", "gender": "性别", "age": "年龄",
        "height": "身高（厘米）", "weight": "体重（公斤）", "concern": "主要问题", "desc": "简要说明",
        "ref": "推荐人", "angel": "关心我的人", "footer": "📩 本报告已通过电子邮件发送。所有内容由 KataChat AI 系统生成，符合 PDPA 规范。"
    },
    "tw": {
        "name": "法定姓名", "dob": "出生日期", "country": "國家", "gender": "性別", "age": "年齡",
        "height": "身高（公分）", "weight": "體重（公斤）", "concern": "主要問題", "desc": "簡要說明",
        "ref": "推薦人", "angel": "關心我的人", "footer": "📩 本報告已通過電子郵件發送。所有內容由 KataChat AI 系統生成，符合 PDPA 標準。"
    }
}

PROMPTS = {
    "en": {
        "summary": lambda age, gender, country, concern, notes:
            f"A {age}-year-old {gender} from {country} is experiencing '{concern}'. Description: {notes}. Write 4 paragraphs of advice in third-person. Avoid using 'you'.",
        "creative": lambda age, gender, country, concern, notes:
            f"As a health coach, give 10 practical suggestions with emojis for a {age}-year-old {gender} from {country} facing '{concern}'. Notes: {notes}."
    }
}

chart_prompts = {
    "en": lambda age, gender, country, concern, notes:
        f"A {age}-year-old {gender} from {country} has the health issue '{concern}'. Notes: {notes}. "
        f"Generate 3 health categories starting with ###, and under each, list 3 real indicators like 'Sleep Quality: 70%'. Use values from 25% to 90%, no repeats."
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
        return result.choices[0].message.content
    except Exception as e:
        logging.error(f"OpenAI error: {e}")
        return "⚠️ Unable to generate response."

def generate_metrics_with_ai(prompt):
    try:
        res = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        lines = res.choices[0].message.content.strip().split("\n")
        metrics = []
        current_title, labels, values = "", [], []
        for line in lines:
            if line.startswith("###"):
                if current_title and labels and values:
                    metrics.append({"title": current_title, "labels": labels, "values": values})
                current_title = line.replace("###", "").strip()
                labels, values = [], []
            elif ":" in line:
                try:
                    label, val = line.split(":", 1)
                    labels.append(label.strip())
                    values.append(int(val.strip().replace("%", "")))
                except:
                    continue
        if current_title and labels and values:
            metrics.append({"title": current_title, "labels": labels, "values": values})
        return metrics or [{"title": "General Health", "labels": ["A", "B", "C"], "values": [60, 60, 60]}]
    except Exception as e:
        logging.error(f"Chart parse error: {e}")
        return [{"title": "General Health", "labels": ["A", "B", "C"], "values": [60, 60, 60]}]

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
        logging.debug(f"POST received: {data}")

        lang = data.get("lang", "en").strip().lower()
        labels = LANGUAGE_TEXTS.get(lang, LANGUAGE_TEXTS["en"])
        content = LANGUAGE.get(lang, LANGUAGE["en"])
        prompts = PROMPTS.get(lang, PROMPTS["en"])
        charts = chart_prompts.get(lang, chart_prompts["en"])

        name = data.get("name")
        dob = data.get("dob")
        gender = data.get("gender")
        height = data.get("height")
        weight = data.get("weight")
        country = data.get("country")
        concern = data.get("condition")
        notes = data.get("details") or "No additional details"
        ref = data.get("referrer")
        angel = data.get("angel")
        age = compute_age(dob)

        metrics = generate_metrics_with_ai(charts(age, gender, country, concern, notes))

        # ✅ CLEAN duplicated 🎉 in AI output
        raw_summary = get_openai_response(prompts["summary"](age, gender, country, concern, notes))
        summary = re.sub(re.escape(content['report_title']), '', raw_summary, flags=re.IGNORECASE).strip()

        raw_creative = get_openai_response(prompts["creative"](age, gender, country, concern, notes), temp=0.85)
        creative = re.sub(re.escape(content['report_title']), '', raw_creative, flags=re.IGNORECASE).strip()

        chart_html = ""
        for m in metrics:
            chart_html += f"<strong>{m['title']}</strong><br>"
            for label, val in zip(m['labels'], m['values']):
                chart_html += (
                    f"<div style='display:flex;align-items:center;margin-bottom:8px;'>"
                    f"<span style='width:180px;'>{label}</span>"
                    f"<div style='flex:1;background:#eee;border-radius:5px;overflow:hidden;'>"
                    f"<div style='width:{val}%;height:14px;background:#5E9CA0;'></div></div>"
                    f"<span style='margin-left:10px;'>{val}%</span></div>"
                )
            chart_html += "<br>"

        email_html = f"<h4 style='text-align:center;'>{content['report_title']}</h4>"
        email_html += chart_html
        email_html += f"<br><div style='font-size:24px; font-weight:bold; margin-top:30px;'>🧠 Summary:</div><br>"
        email_html += ''.join([f"<p style='line-height:1.7; font-size:16px; margin-bottom:16px;'>{p}</p>" for p in summary.split("\n") if p.strip()])
        email_html += f"<br><div style='font-size:24px; font-weight:bold; margin-top:30px;'>💡 Creative Suggestions:</div><br>"
        email_html += ''.join([f"<p style='margin:16px 0; font-size:17px;'>{line}</p>" for line in creative.split("\n") if line.strip()])
        email_html += (
            f"<br><br><p style='font-size:16px;'><strong>🛡️ Disclaimer:</strong></p>"
            f"<p style='font-size:15px; line-height:1.6;'>🩺 This platform offers general lifestyle suggestions. "
            f"Please consult a licensed medical professional for diagnosis or treatment decisions.</p>"
        )
        email_html += f"<p style='color:#888;margin-top:20px;'>{labels['footer']}</p>"

        html_result = f"<h4 style='text-align:center;'>{content['report_title']}</h4>"
        html_result += f"<br><div style='font-size:24px; font-weight:bold; margin-top:30px;'>🧠 Summary:</div><br>"
        html_result += ''.join([f"<p style='line-height:1.7; font-size:16px; margin-bottom:16px;'>{p}</p>" for p in summary.split("\n") if p.strip()])
        html_result += f"<br><div style='font-size:24px; font-weight:bold; margin-top:30px;'>💡 Creative Suggestions:</div><br>"
        html_result += ''.join([f"<p style='margin:16px 0; font-size:17px;'>{line}</p>" for line in creative.split("\n") if line.strip()])
        html_result += (
            f"<br><br><p style='font-size:16px;'><strong>🛡️ Disclaimer:</strong></p>"
            f"<p style='font-size:15px; line-height:1.6;'>🩺 This platform offers general lifestyle suggestions. "
            f"Please consult a licensed medical professional for diagnosis or treatment decisions.</p>"
        )
        html_result += f"<p style='color:#888;margin-top:20px;'>{labels['footer']}</p>"

        send_email(email_html, lang)

        return jsonify({
            "metrics": metrics,
            "html_result": html_result,
            "footer": labels['footer']
        })

    except Exception as e:
        logging.error(f"Health analyze error: {e}")
        traceback.print_exc()
        return jsonify({"error": "Server error"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 5000)), host="0.0.0.0")
