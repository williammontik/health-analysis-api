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
        "creative_header": "💡 Creative Support Ideas",
        "fallback_error": "⚠️ Sorry, something went wrong. Please try again.",
        "footer": "<div style=\"background-color:#e6f7ff; color:#00529B; padding:15px; border-left:4px solid #00529B; margin:20px 0;\"><strong>Insights generated through analysis of:</strong><br>1. Our medical profiles database<br>2. Global health benchmarks<br><em>All data processed with strict compliance.</em></div>"
    },
    "zh": {
        "email_subject": "您的健康洞察报告",
        "report_title": "🎉 全球健康洞察（简体）",
        "creative_header": "💡 创意支持建议",
        "fallback_error": "⚠️ 抱歉，目前系统忙碌，请稍后再试。",
        "footer": "<div style=\"background-color:#e6f7ff; color:#00529B; padding:15px; border-left:4px solid #00529B; margin:20px 0;\"><strong>本报告通过分析以下数据生成:</strong><br>1. 匿名医疗资料库<br>2. 全球健康基准数据<br><em>所有数据处理均符合隐私保护法规</em></div>"
    },
    "tw": {
        "email_subject": "您的健康洞察報告",
        "report_title": "🎉 全球健康洞察（繁體）",
        "creative_header": "💡 創意支持建議",
        "fallback_error": "⚠️ 抱歉，系統忙碌中，請稍後再試。",
        "footer": "<div style=\"background-color:#e6f7ff; color:#00529B; padding:15px; border-left:4px solid #00529B; margin:20px 0;\"><strong>本報告通過分析以下數據生成:</strong><br>1. 匿名醫療資料庫<br>2. 全球健康基準數據<br><em>所有數據處理均符合隱私保護法規</em></div>"
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

def ask_gpt(prompt, temp=0.7):
    try:
        result = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=temp
        )
        return result.choices[0].message.content
    except Exception as e:
        logging.warning(f"GPT error: {e}")
        return ""

def translate(text, lang="zh"):
    if lang == "en": return text
    instruction = "请将以下内容翻译为简体中文：" if lang == "zh" else "請將以下內容翻譯為繁體中文："
    try:
        result = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"{instruction}\n\n{text}"}],
            temperature=0.4
        )
        return result.choices[0].message.content.replace("\n", "<br>")
    except:
        return text

@app.route("/health_analyze", methods=["POST"])
def health_analyze():
    try:
        data = request.get_json(force=True)
        lang = data.get("lang", "en")
        content = LANGUAGE.get(lang, LANGUAGE["en"])

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

        metrics_prompt = f"Generate 3 health sections for a {age}-year-old {gender} in {country} with concern '{concern}'. Each starts with ### Title, and has 3 lines like 'Label: 70%'"
        summary_prompt = f"A {age}-year-old {gender} from {country} has a health concern: {concern}. Description: {notes}. Write 4 helpful paragraphs."
        creative_prompt = f"Suggest 10 creative health ideas for someone in {country}, age {age}, gender {gender}, with concern '{concern}'. Note: {notes}."

        metrics_raw = ask_gpt(metrics_prompt)
        summary_raw = ask_gpt(summary_prompt)
        creative_raw = ask_gpt(creative_prompt, temp=0.85)

        metrics = []
        current_title, labels, values = "", [], []
        for line in metrics_raw.split("\n"):
            if line.startswith("###"):
                if current_title and labels and values:
                    metrics.append({"title": current_title, "labels": labels, "values": values})
                current_title, labels, values = line[3:].strip(), [], []
            elif ":" in line:
                label, val = line.split(":", 1)
                labels.append(label.strip())
                try: values.append(int(val.strip().replace("%", "")))
                except: values.append(50)
        if current_title and labels and values:
            metrics.append({"title": current_title, "labels": labels, "values": values})

        summary = translate(summary_raw, lang)
        creative = translate(creative_raw, lang)

        chart_html = ""
        for m in metrics:
            chart_html += f"<strong>{m['title']}</strong><br>"
            for l, v in zip(m['labels'], m['values']):
                chart_html += f"<div style='display:flex; align-items:center; margin-bottom:8px;'><span style='width:180px;'>{l}</span><div style='flex:1; background:#eee; border-radius:5px; overflow:hidden;'><div style='width:{v}%; height:14px; background:#5E9CA0;'></div></div><span style='margin-left:10px;'>{v}%</span></div>"
            chart_html += "<br>"

        creative_html = f"<br><br><h3 style='font-size:24px; font-weight:bold;'>{content['creative_header']}</h3><br>"
        creative_html += creative

        html_output = (
            f"<h4 style='text-align:center; font-size:24px;'>{content['report_title']}</h4>"
            f"<p><strong>姓名:</strong> {name}<br><strong>出生:</strong> {dob}<br><strong>国家:</strong> {country}<br><strong>性别:</strong> {gender}<br><strong>年龄:</strong> {age}<br><strong>身高:</strong> {height} cm<br><strong>体重:</strong> {weight} kg<br><strong>主问题:</strong> {concern}<br><strong>说明:</strong> {notes}<br><strong>推荐人:</strong> {ref}<br><strong>关心者:</strong> {angel}</p>"
            f"{chart_html}{summary}<br>{creative_html}{content['footer']}"
        )

        send_email(html_output, lang)

        return jsonify({
            "metrics": metrics,
            "analysis": summary,
            "creative": creative_html,
            "footer": content['footer']
        })

    except Exception as e:
        app.logger.error(f"Health analyze error: {e}")
        return jsonify({"error": LANGUAGE.get(lang, LANGUAGE['en'])["fallback_error"]}), 500

if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 5000)), host="0.0.0.0")
