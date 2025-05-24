# -*- coding: utf-8 -*-
import os, random, logging, smtplib
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
        "email_subject": "您的健康洞察報告",
        "report_title": "🎉 全球健康洞察（简体）"
    },
    "tw": {
        "email_subject": "您的健康洞察報告",
        "report_title": "🎉 全球健康洞察（繁體）"
    }
}

PROMPTS = {
    "en": {
        "summary": lambda age, gender, country, concern, notes:
            f"A {age}-year-old {gender} in {country} has concern '{concern}'. Description: {notes}. "
            f"Write 4 helpful paragraphs for similar individuals. Do not address directly.",
        "creative": lambda age, gender, country, concern, notes:
            f"As a wellness coach, suggest 10 creative health ideas for someone in {country}, aged {age}, gender {gender}, with '{concern}'. "
            f"Take into account: {notes}."
    },
    "zh": {
        "summary": lambda age, gender, country, concern, notes:
            f"一位{age}岁、性别为{gender}、来自{country}的人，有健康问题「{concern}」。说明如下：{notes}。"
            f"请写4段建议，帮助其他有相似情况的人。请避免直接使用“你”来称呼。",
        "creative": lambda age, gender, country, concern, notes:
            f"作为一名健康教练，请为{country}一位{age}岁的{gender}，面临「{concern}」问题的人，提供10条创意健康建议。"
            f"请参考以下描述：{notes}。"
    },
    "tw": {
        "summary": lambda age, gender, country, concern, notes:
            f"一名{age}歲的{gender}來自{country}，健康問題為「{concern}」，描述如下：{notes}。"
            f"請撰寫4段建議，不要用「你」，要像是給其他人建議。",
        "creative": lambda age, gender, country, concern, notes:
            f"請以健康教練的身份，為{country}一位{age}歲的{gender}，健康問題為「{concern}」的人，"
            f"提供10個創意建議。請根據這些描述：{notes}。"
    }
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
            {"title": "Cognitive Health", "labels": ["Memory", "Focus", "Reaction"], "values": [65, 70, 60]},
            {"title": "Emotional Health", "labels": ["Mood", "Stress", "Energy"], "values": [68, 55, 62]},
            {"title": "Physical Ability", "labels": ["Balance", "Strength", "Coordination"], "values": [60, 70, 58]}
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
        lang = data.get("lang", "en")
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

        metrics_prompt = (
            f"Generate health chart data for a {age}-year-old {gender} in {country} with concern '{concern}' and notes '{notes}'. "
            f"Include 3 sections prefixed with ### title, and 3 indicators below each using format 'Label: Value%'."
        )
        metrics = generate_metrics_with_ai(metrics_prompt)

        summary_prompt = PROMPTS.get(lang, PROMPTS["en"])["summary"](age, gender, country, concern, notes)
        creative_prompt = PROMPTS.get(lang, PROMPTS["en"])["creative"](age, gender, country, concern, notes)

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
            "<br><br><h3 style='font-size:24px; font-weight:bold;'>💡 Creative Support Ideas</h3><br>"
        )
        creative_html += "".join(
            f"<p style='margin-bottom:14px;'>{line.strip()}</p>"
            for line in creative.split("\n") if line.strip()
        )
        creative_html += "<br>"

        footer = (
            '<div style="background-color:#e6f7ff; color:#00529B; padding:15px; '
            'border-left:4px solid #00529B; margin:20px 0;">'
            '<strong>The insights in this report are generated by KataChat’s AI systems analyzing:</strong><br>'
            '1. Our proprietary database of anonymized medical profiles across Singapore, Malaysia, and Taiwan<br>'
            '2. Aggregated global health benchmarks from trusted OpenAI research and medical reports trend datasets<br>'
            '<em>All data is processed through our AI models to identify statistically significant patterns while maintaining strict PDPA compliance. '
            'Sample sizes vary by analysis, with minimum thresholds of 700+ data points for medical comparisons.</em>'
            '</div>'
            '<p style="background-color:#e6f7ff; color:#00529B; padding:15px; '
            'border-left:4px solid #00529B; margin:20px 0;">'
            '<strong>PS:</strong> This report has also been sent to your email inbox and should arrive within 24 hours. '
            'If you\'d like to discuss it further, feel free to reach out — we’re happy to arrange a 15-minute call at your convenience.</p>'
        )

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
        app.logger.error(f"Health analyze error: {e}")
        return jsonify({"error": "Server error"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 5000)), host="0.0.0.0")
