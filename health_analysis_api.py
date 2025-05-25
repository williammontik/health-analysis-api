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

PROMPTS = {
    "en": {
        "summary": lambda age, gender, country, concern, notes:
            f"A {age}-year-old {gender} from {country} is experiencing \"{concern}\". Description: {notes}. "
            f"Write a brief health summary with statistics showing how similar people manage this condition. Avoid using 'you'.",
        "creative": lambda age, gender, country, concern, notes:
            f"As a health coach, suggest 10 creative tips for a {age}-year-old {gender} in {country} dealing with \"{concern}\". "
            f"Include relatable emojis and % stats if helpful. Base on: {notes}"
    },
    "zh": {
        "summary": lambda age, gender, country, concern, notes:
            f"一位{age}岁{gender}，来自{country}，主要健康问题为「{concern}」，补充说明：{notes}。"
            f"请撰写一段简要的健康摘要，包含统计数据，说明类似人群如何处理该问题。避免使用“你”。",
        "creative": lambda age, gender, country, concern, notes:
            f"请以健康教练的身份，为{country}一位{age}岁{gender}提出10个创意健康建议，应对「{concern}」。"
            f"建议中加入表情符号与百分比统计会更真实。补充说明：{notes}"
    },
    "tw": {
        "summary": lambda age, gender, country, concern, notes:
            f"一名{age}歲的{gender}來自{country}，健康問題為「{concern}」，補充說明：{notes}。"
            f"請撰寫一段摘要，說明與他相似的人如何應對此問題，並加入統計數據。避免使用「你」。",
        "creative": lambda age, gender, country, concern, notes:
            f"請以健康教練身份，為{country}一位{age}歲的{gender}提出10則創意健康建議來處理「{concern}」。"
            f"請使用表情符號與百分比資料會更生動。補充內容：{notes}"
    }
}

chart_prompts = {
    "en": lambda age, gender, country, concern, notes:
        f"Generate health chart data for a {age}-year-old {gender} in {country} with \"{concern}\". Notes: {notes}. "
        f"Output 3 sections starting with ###, each with 3 indicators in format: Indicator: Value%",
    "zh": lambda age, gender, country, concern, notes:
        f"为{country}的{age}岁{gender}生成健康图表资料，主要问题「{concern}」，补充说明：{notes}。"
        f"以###开头分为3类，每类3项，格式为：指标: 数值%",
    "tw": lambda age, gender, country, concern, notes:
        f"請為{country}一位{age}歲{gender}產生健康圖表資料，主要問題為「{concern}」，補充：{notes}。"
        f"請用 ### 開頭分3類，每類3項指標，格式為「指標: 數值%」。"
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
        labels, values = [], []
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
                    values.append(random.randint(50, 80))
        if current_title and labels and values:
            metrics.append({
                "title": current_title,
                "labels": labels,
                "values": values
            })
        if not metrics:
            raise ValueError("GPT chart returned no metrics.")
        return metrics
    except Exception as e:
        logging.warning(f"GPT metric error: {e}")
        return [
            {"title": "General Wellness", "labels": ["Energy", "Stress", "Focus"], "values": [60, 65, 70]},
            {"title": "Body Response", "labels": ["Hydration", "Mobility", "Pain"], "values": [62, 67, 69]},
            {"title": "Daily Habits", "labels": ["Routine", "Nutrition", "Sleep"], "values": [70, 75, 72]}
        ]

def get_openai_response(prompt, temp=0.75):
    try:
        result = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=temp
        )
        return result.choices[0].message.content
    except Exception as e:
        app.logger.error(f"OpenAI response error: {e}")
        return "⚠️ Unable to generate content."

@app.route("/health_analyze", methods=["POST"])
def health_analyze():
    try:
        data = request.get_json(force=True)
        lang     = data.get("lang", "en").strip()
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
        labels   = LANGUAGE.get(lang, LANGUAGE["en"])

        metrics_prompt   = chart_prompts.get(lang, chart_prompts["en"])(age, gender, country, concern, notes)
        summary_prompt   = PROMPTS.get(lang, PROMPTS["en"])["summary"](age, gender, country, concern, notes)
        creative_prompt  = PROMPTS.get(lang, PROMPTS["en"])["creative"](age, gender, country, concern, notes)

        metrics  = generate_metrics_with_ai(metrics_prompt)
        summary  = get_openai_response(summary_prompt)
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

        creative_html = f"<br><br><h3 style='font-size:24px; font-weight:bold;'>{labels['creative_title']}</h3><br>"
        creative_html += "".join(
            f"<p style='margin-bottom:14px;'>{line.strip()}</p>"
            for line in creative.split("\n") if line.strip()
        )

        footer = f"<p style='color:#888;'>{labels['disclaimer']}</p>"
        html = (
            f"<h4 style='text-align:center; font-size:24px;'>{labels['report_title']}</h4>"
            f"<p><strong>Full Name:</strong> {name}<br><strong>Date of Birth:</strong> {dob}<br>"
            f"<strong>Country:</strong> {country}<br><strong>Gender:</strong> {gender}<br><strong>Age:</strong> {age}<br>"
            f"<strong>Height:</strong> {height} cm<br><strong>Weight:</strong> {weight} kg<br>"
            f"<strong>Concern:</strong> {concern}<br><strong>Description:</strong> {notes}<br>"
            f"<strong>Referrer:</strong> {ref}<br><strong>Caring Person:</strong> {angel}</p>"
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
