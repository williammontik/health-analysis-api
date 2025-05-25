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
        "report_title": "🎉 Global Identical Health Insights"
    },
    "zh": {
        "email_subject": "您的健康洞察报告",
        "report_title": "🎉 全球健康洞察（简体）"
    },
    "tw": {
        "email_subject": "您的健康洞察報告",
        "report_title": "🎉 全球健康洞察（繁體）"
    }
}

PROMPTS = {
    "tw": {
        "summary": lambda age, gender, country, concern, notes:
            f"一名{age}歲的{gender}來自{country}，健康問題為「{concern}」，描述如下：{notes}。請撰寫4段建議，不要用「你」，要像是給其他人建議。",
        "creative": lambda age, gender, country, concern, notes:
            f"請以健康教練的身份，為{country}一位{age}歲的{gender}，健康問題為「{concern}」的人，提供10個創意建議。請根據這些描述：{notes}。"
    },
    "zh": {
        "summary": lambda age, gender, country, concern, notes:
            f"一位{age}歲的{gender}來自{country}，主要健康問題是「{concern}」。補充說明：{notes}。請給出4段建議，避免使用「你」，更像是對他人提出的建議。",
        "creative": lambda age, gender, country, concern, notes:
            f"請以健康教練的身份，為{country}一位{age}歲的{gender}，健康問題為「{concern}」，提出10個創意建議。說明如下：{notes}"
    },
    "en": {
        "summary": lambda age, gender, country, concern, notes:
            f"A {age}-year-old {gender} from {country} is experiencing '{concern}'. Description: {notes}. Please write 4 pieces of advice in a professional, third-person tone (avoid using 'you').",
        "creative": lambda age, gender, country, concern, notes:
            f"As a health coach, provide 10 creative and practical suggestions for a {age}-year-old {gender} from {country} who is dealing with '{concern}'. Extra notes: {notes}."
    }
}

chart_prompts = {
    "en": lambda age, gender, country, concern, notes:
        f"A {age}-year-old {gender} from {country} is facing a health concern: '{concern}'. Additional notes: {notes}. "
        f"Please create 3 chart categories that reflect this specific concern — for example, if the issue is diabetes, use themes like 'Blood Sugar Control', 'Diet Compliance', 'Physical Activity'. "
        f"For each category, use a heading starting with ###. Under each, list 3 meaningful health indicators in the format 'Indicator: Value%'. "
        f"Ensure values are varied (between 25% and 90%) and avoid using the same number repeatedly. Make sure categories and indicators are medically relevant.",

    "zh": lambda age, gender, country, concern, notes:
        f"一位{age}歲的{gender}來自{country}，主要健康問題是「{concern}」。補充說明：{notes}。請根據此問題產生3個與健康有關的圖表分類，例如如果是糖尿病，可以用「血糖控制」、「飲食管理」、「運動習慣」。"
        f"每個分類請用 ### 作為開頭，然後列出3個具體指標，格式為「指標: 數值%」。請確保數值介於25%到90%之間，避免使用相同數字，並使每個指標和分類與此健康問題緊密相關。",

    "tw": lambda age, gender, country, concern, notes:
        f"這位{age}歲的{gender}來自{country}，目前的健康困擾是「{concern}」。補充說明如下：{notes}。請根據此健康問題設計3個對應的圖表分類，例如若問題為高血壓，可使用「血壓監控」、「飲食習慣」、「壓力管理」。"
        f"每個分類請以 ### 開頭，底下列出3項相關健康指標，格式為「指標: 數值%」。請確保每個數值在25%到90%之間，且不要重複同樣的數字。所有內容需貼近實際健康情境。"
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
            metrics.append({
                "title": current_title,
                "labels": labels,
                "values": values
            })
        if not metrics:
            raise ValueError("GPT returned no metrics.")
        return metrics
    except Exception as e:
        logging.warning(f"GPT metric error: {e}")
        return [
            {"title": "General Health", "labels": ["Indicator A", "Indicator B", "Indicator C"], "values": [60, 60, 60]}
        ]

def get_openai_response(prompt, temp=0.7):
    try:
        result = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=temp
        )
        return result.choices[0].message.content
    except Exception as e:
        app.logger.error(f"OpenAI error: {e}")
        return "⚠️ 無法生成內容。"

@app.route("/health_analyze", methods=["POST"])
def health_analyze():
    try:
        data = request.get_json(force=True)
        lang = data.get("lang", "en").strip()
        if lang not in LANGUAGE:
            lang = "tw"  # fallback to Traditional Chinese

        content = LANGUAGE[lang]
        prompts = PROMPTS[lang]
        charts = chart_prompts[lang]

        name     = data.get("name")
        dob      = data.get("dob")
        gender   = data.get("gender")
        height   = data.get("height")
        weight   = data.get("weight")
        country  = data.get("country")
        concern  = data.get("condition")
        notes    = data.get("details", "") or "沒有提供補充說明。"
        ref      = data.get("referrer")
        angel    = data.get("angel")
        age      = compute_age(dob)

        metrics_prompt = charts(age, gender, country, concern, notes)
        metrics = generate_metrics_with_ai(metrics_prompt)

        summary_prompt = prompts["summary"](age, gender, country, concern, notes)
        creative_prompt = prompts["creative"](age, gender, country, concern, notes)

        summary = get_openai_response(summary_prompt)
        creative = get_openai_response(creative_prompt, temp=0.85)

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

        creative_html = (
            "<br><br><h3 style='font-size:24px; font-weight:bold;'>💡</h3><br>"
        )
        creative_html += "".join(
            f"<p style='margin-bottom:14px;'>{line.strip()}</p>"
            for line in creative.split("\n") if line.strip()
        )
        creative_html += "<br>"

        footer = (
            "<p style='color:#888;'>📩 本報告已通過電子郵件發送。所有內容由 KataChat AI 系統生成，符合 PDPA 標準。</p>"
        )

        html = (
            f"<h4 style='text-align:center; font-size:24px;'>{content['report_title']}</h4>"
            f"<p><strong>法定姓名:</strong> {name}<br><strong>出生日期:</strong> {dob}<br>"
            f"<strong>國家:</strong> {country}<br><strong>性別:</strong> {gender}<br><strong>年齡:</strong> {age}<br>"
            f"<strong>身高:</strong> {height} cm<br><strong>體重:</strong> {weight} kg<br>"
            f"<strong>主要問題:</strong> {concern}<br><strong>簡要說明:</strong> {notes}<br>"
            f"<strong>推薦人:</strong> {ref}<br><strong>關心我的人:</strong> {angel}</p>"
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
        app.logger.error(f"Health analyze error: {e}")
        return jsonify({"error": "Server error"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 5000)), host="0.0.0.0")
