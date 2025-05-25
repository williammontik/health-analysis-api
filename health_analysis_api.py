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
    "en": {
        "email_subject": "Your Health Insight Report",
        "report_title": "🎉 Global Identical Health Insights",
        "disclaimer": "🩺 This platform offers general lifestyle suggestions. Please consult a licensed medical professional for diagnosis or treatment decisions."
    },
    "zh": {
        "email_subject": "您的健康洞察報告",
        "report_title": "🎉 全球健康洞察（简体）",
        "disclaimer": "🩺 本平台僅提供一般生活建議，請向指導醫師進行小心評估。"
    },
    "tw": {
        "email_subject": "您的健康洞察報告",
        "report_title": "🎉 全球健康洞察（繁體）",
        "disclaimer": "🩺 本平台僅提供一般生活建議，請諮詢專業醫師以獲得評估或治療建議。"
    }
}

PROMPTS = {
    "tw": {
        "summary": lambda age, gender, country, concern, notes:
            f"針對一位年約 {age} 歲、性別為 {gender}、居住在 {country}、健康狀況為「{concern}」的典型個案，說明如下：{notes}。\n請用第三人稱撰寫 4 段健康觀察與建議，避免使用『你』字。",
        "creative": lambda age, gender, country, concern, notes:
            f"作為一名健康教練，請提供 10 個創意建議，幫助一位約 {age} 歲、性別 {gender}、來自 {country}、健康問題為「{concern}」的人改善生活。補充說明：{notes}。"
    },
    "zh": {
        "summary": lambda age, gender, country, concern, notes:
            f"針對一位年齡約 {age} 歲、性別為 {gender}、來自 {country}、健康問題為「{concern}」的人，根據以下描述：{notes}，請撰寫 4 段客觀的健康建議，以第三人稱撰寫，不使用『你』。",
        "creative": lambda age, gender, country, concern, notes:
            f"請作為健康生活顧問，為來自 {country}、約 {age} 歲的 {gender}，健康挑戰為「{concern}」，提供 10 條創意建議。補充說明：{notes}。"
    },
    "en": {
        "summary": lambda age, gender, country, concern, notes:
            f"This represents a typical case of a {age}-year-old {gender} living in {country}, experiencing '{concern}'. Description: {notes}. Please write 4 brief lifestyle insights and tips in third-person tone. Do not use 'you'.",
        "creative": lambda age, gender, country, concern, notes:
            f"As a health coach, provide 10 creative and practical suggestions for someone aged {age}, gender {gender}, living in {country}, with the health concern '{concern}'. Additional details: {notes}."
    }
}

chart_prompts = {
    "tw": lambda age, gender, country, concern, notes:
        f"請為一位年約 {age} 歲、{gender}、來自 {country}、健康問題是「{concern}」的人產生健康圖表數據，補充說明：{notes}。\n分為三類，以 ### 開頭作為分類標題，每類列出三項指標，格式為「指標: 數值%」。",
    "zh": lambda age, gender, country, concern, notes:
        f"請為一位來自 {country}、年齡約 {age} 歲、性別為 {gender}、健康問題是「{concern}」的案例產生健康圖表資料，補充說明：{notes}。\n請用 ### 開頭分成三個分類，並為每類列出三個指標，格式為「指標: 數值%」。",
    "en": lambda age, gender, country, concern, notes:
        f"Generate health metric data for a typical {age}-year-old {gender} in {country}, with the concern '{concern}'. Description: {notes}.\nCreate 3 sections with headings starting with ###. Each section should list 3 indicators in 'Indicator: Value%' format."
}

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

def generate_metrics_with_ai(prompt_text):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt_text}],
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
                    metrics.append({"title": current_title, "labels": labels, "values": values})
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
        return metrics
    except Exception as e:
        logging.warning(f"GPT metric error: {e}")
        return [
            {"title": "Cognitive Health", "labels": ["Memory", "Focus", "Reaction"], "values": [65, 70, 60]},
            {"title": "Emotional Well-being", "labels": ["Mood", "Stress", "Energy"], "values": [68, 55, 62]},
            {"title": "Physical Condition", "labels": ["Balance", "Strength", "Coordination"], "values": [60, 70, 58]}
        ]

def get_openai_response(prompt, temp=0.7):
    try:
        result = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=temp
        )
        return result.choices[0].message.content.strip()
    except Exception as e:
        app.logger.error(f"OpenAI error: {e}")
        return "⚠️ Unable to generate content."

@app.route("/health_analyze", methods=["POST"])
def health_analyze():
    try:
        data = request.get_json(force=True)
        lang = data.get("lang", "en").strip()
        content = LANGUAGE.get(lang, LANGUAGE["en"])

        name = data.get("name")
        dob = data.get("dob")
        gender = data.get("gender")
        height = data.get("height")
        weight = data.get("weight")
        country = data.get("country")
        concern = data.get("condition")
        notes = data.get("details", "") or "No additional description provided."
        ref = data.get("referrer")
        angel = data.get("angel")
        age = compute_age(dob)

        metric_prompt = chart_prompts.get(lang, chart_prompts["en"])(age, gender, country, concern, notes)
        summary_prompt = PROMPTS.get(lang, PROMPTS["en"])["summary"](age, gender, country, concern, notes)
        creative_prompt = PROMPTS.get(lang, PROMPTS["en"])["creative"](age, gender, country, concern, notes)

        metrics = generate_metrics_with_ai(metric_prompt)
        summary = get_openai_response(summary_prompt)
        creative = get_openai_response(creative_prompt, temp=0.85)
        disclaimer = content["disclaimer"]

        chart_html = ""
        for m in metrics:
            chart_html += f"<strong>{m['title']}</strong><br>"
            for label, value in zip(m['labels'], m['values']):
                chart_html += (
                    f"<div style='display:flex; align-items:center; margin-bottom:8px;'>"
                    f"<span style='width:180px;'>{label}</span>"
                    f"<div style='flex:1; background:#eee; border-radius:5px; overflow:hidden;'>"
                    f"<div style='width:{value}%; height:14px; background:#5E9CA0;'></div>"
                    f"</div><span style='margin-left:10px;'>{value}%</span></div>"
                )
            chart_html += "<br>"

        creative_html = (
            "<br><br><h3 style='font-size:24px; font-weight:bold;'>💡 Creative Health Suggestions</h3><br>"
        )
        creative_html += "".join(
            f"<p style='margin-bottom:14px;'>{line.strip()}</p>"
            for line in creative.split("\n") if line.strip()
        )

        footer = f"<p style='color:#888;'>{disclaimer}</p>"

        html = (
            f"<h4 style='text-align:center; font-size:24px;'>{content['report_title']}</h4>"
            f"<p><strong>Given Legal Name:</strong> {name}<br><strong>Date of Birth:</strong> {dob}<br>"
            f"<strong>Country:</strong> {country}<br><strong>Gender:</strong> {gender}<br><strong>Age:</strong> {age}<br>"
            f"<strong>Height:</strong> {height} cm<br><strong>Weight:</strong> {weight} kg<br>"
            f"<strong>Main Concern:</strong> {concern}<br><strong>Description:</strong> {notes}<br>"
            f"<strong>Referrer:</strong> {ref}<br><strong>Caring Person:</strong> {angel}</p>"
            f"{chart_html}<div>{summary}</div>{creative_html}{footer}"
        )

        send_email(html, lang)

        return jsonify({
            "metrics": metrics,
            "analysis": summary,
            "creative": creative_html,
            "footer": footer
        })

    except Exception as e:
        app.logger.error(f"Health analyze error: {e}")
        return jsonify({"error": "Server error"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 5000)), host="0.0.0.0")
