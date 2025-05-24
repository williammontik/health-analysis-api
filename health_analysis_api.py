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
        "report_title": "🎉 Global Health Insights",
        "response_lang": "Respond in English",
        "creative_header": "💡 Creative Support Ideas",
        "footer": """<div style="background-color:#e6f7ff; color:#00529B; padding:15px; border-left:4px solid #00529B; margin:20px 0;">
            <strong>Insights generated through analysis of:</strong><br>
            1. Our medical profiles database<br>
            2. Global health benchmarks<br>
            <em>All data processed with strict compliance.</em>
        </div>"""
    },
    "zh": {
        "email_subject": "您的健康洞察报告",
        "report_title": "🎉 全球健康洞察（简体）",
        "response_lang": "请用简体中文回答",
        "creative_header": "💡 创意支持建议",
        "footer": """<div style="background-color:#e6f7ff; color:#00529B; padding:15px; border-left:4px solid #00529B; margin:20px 0;">
            <strong>本报告通过分析以下数据生成:</strong><br>
            1. 匿名医疗资料库<br>
            2. 全球健康基准数据<br>
            <em>所有数据处理均符合隐私保护法规</em>
        </div>"""
    },
    "tw": {
        "email_subject": "您的健康洞察報告",
        "report_title": "🎉 全球健康洞察（繁體）",
        "response_lang": "請用繁體中文回答",
        "creative_header": "💡 創意支持建議",
        "footer": """<div style="background-color:#e6f7ff; color:#00529B; padding:15px; border-left:4px solid #00529B; margin:20px 0;">
            <strong>本報告通過分析以下數據生成:</strong><br>
            1. 匿名醫療資料庫<br>
            2. 全球健康基準數據<br>
            <em>所有數據處理均符合隱私保護法規</em>
        </div>"""
    }
}

def send_email(html_body, lang):
    subject = LANGUAGE[lang]["email_subject"]
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

def generate_metrics_with_ai(prompt_text, lang="en"):
    try:
        lang_instruction = LANGUAGE.get(lang, {}).get("response_lang", "")
        full_prompt = f"{prompt_text} {lang_instruction}"
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": full_prompt}],
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
                try: values.append(int(val.strip().replace("%", "")))
                except: values.append(50)
        if current_title and labels and values:
            metrics.append({"title": current_title, "labels": labels, "values": values})
        return metrics
    except Exception as e:
        logging.warning(f"GPT metric error: {e}")
        if lang == "zh":
            return [
                {"title": "认知健康", "labels": ["记忆", "专注", "反应"], "values": [65, 70, 60]},
                {"title": "情绪健康", "labels": ["情绪", "压力", "能量"], "values": [68, 55, 62]},
                {"title": "身体能力", "labels": ["平衡", "力量", "协调"], "values": [60, 70, 58]}
            ]
        elif lang == "tw":
            return [
                {"title": "認知健康", "labels": ["記憶", "專注", "反應"], "values": [65, 70, 60]},
                {"title": "情緒健康", "labels": ["情緒", "壓力", "能量"], "values": [68, 55, 62]},
                {"title": "身體能力", "labels": ["平衡", "力量", "協調"], "values": [60, 70, 58]}
            ]
        return [
            {"title": "Cognitive Health", "labels": ["Memory", "Focus", "Reaction"], "values": [65, 70, 60]},
            {"title": "Emotional Health", "labels": ["Mood", "Stress", "Energy"], "values": [68, 55, 62]},
            {"title": "Physical Ability", "labels": ["Balance", "Strength", "Coordination"], "values": [60, 70, 58]}
        ]

def get_openai_response(prompt, lang="en", temp=0.7):
    try:
        lang_instruction = LANGUAGE.get(lang, {}).get("response_lang", "")
        full_prompt = f"{prompt} {lang_instruction}"
        
        result = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": full_prompt}],
            temperature=temp
        )
        return result.choices[0].message.content
    except Exception as e:
        app.logger.error(f"OpenAI error: {e}")
        return "⚠️ 無法生成內容。" if lang in ["zh", "tw"] else "⚠️ Content generation failed."

@app.route("/health_analyze", methods=["POST"])
def health_analyze():
    try:
        data = request.get_json(force=True)
        lang = data.get("lang", "en")
        content = LANGUAGE.get(lang, LANGUAGE["en"])

        # Extract parameters
        name = data.get("name")
        dob = data.get("dob")
        gender = data.get("gender")
        height = data.get("height")
        weight = data.get("weight")
        country = data.get("country")
        concern = data.get("condition")
        notes = data.get("details", "") or ("无详细说明" if lang in ["zh", "tw"] else "No details provided")
        ref = data.get("referrer")
        angel = data.get("angel")
        age = compute_age(dob)

        # Generate content
        metrics_prompt = (
            f"Generate health chart data for a {age}-year-old {gender} in {country} "
            f"with concern '{concern}' and notes '{notes}'. "
            f"Include 3 sections prefixed with ### title, and 3 indicators below each using format 'Label: Value%'."
        )
        metrics = generate_metrics_with_ai(metrics_prompt, lang)

        summary_prompt = (
            f"A {age}-year-old {gender} in {country} has concern '{concern}'. Description: {notes}. "
            f"Write 4 helpful paragraphs for similar individuals."
        )
        creative_prompt = (
            f"As a wellness coach, suggest 10 creative health ideas for someone in {country}, "
            f"aged {age}, gender {gender}, with '{concern}'. Take into account: {notes}."
        )

        summary = get_openai_response(summary_prompt, lang)
        creative = get_openai_response(creative_prompt, lang, temp=0.85)

        # Build HTML
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

        creative_html = f"<br><br><h3 style='font-size:24px; font-weight:bold;'>{content['creative_header']}</h3><br>"
        creative_html += "".join(
            f"<p style='margin-bottom:14px;'>{line.strip()}</p>"
            for line in creative.split("\n") if line.strip()
        )

        html = (
            f"<h4 style='text-align:center; font-size:24px;'>{content['report_title']}</h4>"
            f"<p><strong>{'法定姓名' if lang in ['zh','tw'] else 'Legal Name'}:</strong> {name}<br>"
            f"<strong>{'出生日期' if lang in ['zh','tw'] else 'Date of Birth'}:</strong> {dob}<br>"
            f"<strong>{'国家' if lang == 'zh' else '國家' if lang == 'tw' else 'Country'}:</strong> {country}<br>"
            f"<strong>{'性别' if lang in ['zh','tw'] else 'Gender'}:</strong> {gender}<br>"
            f"<strong>{'年龄' if lang in ['zh','tw'] else 'Age'}:</strong> {age}<br>"
            f"<strong>{'身高' if lang in ['zh','tw'] else 'Height'}:</strong> {height} {'公分' if lang == 'tw' else '厘米' if lang == 'zh' else 'cm'}<br>"
            f"<strong>{'体重' if lang in ['zh','tw'] else 'Weight'}:</strong> {weight} {'公斤' if lang in ['zh','tw'] else 'kg'}<br>"
            f"<strong>{'主要问题' if lang in ['zh','tw'] else 'Main Concern'}:</strong> {concern}<br>"
            f"<strong>{'简要说明' if lang == 'zh' else '簡要說明' if lang == 'tw' else 'Description'}:</strong> {notes}<br>"
            f"<strong>{'推荐人' if lang in ['zh','tw'] else 'Referrer'}:</strong> {ref}<br>"
            f"<strong>{'关心者' if lang in ['zh','tw'] else 'Angel'}:</strong> {angel}</p>"
            f"{chart_html}"
            f"<div>{summary}</div>"
            f"{creative_html}"
            f"{content['footer']}"
        )

        send_email(html, lang)

        return jsonify({
            "metrics": metrics,
            "analysis": summary,
            "creative": creative_html,
            "footer": content['footer']
        })

    except Exception as e:
        app.logger.error(f"Health analyze error: {e}")
        return jsonify({"error": "Server error"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 5000)), host="0.0.0.0")
