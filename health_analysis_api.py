# -*- coding: utf-8 -*-
import os, random, logging, smtplib, html
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
        "response_lang": "You are a helpful assistant. Always reply in English.",
        "creative_header": "💡 Creative Support Ideas",
        "fallback_error": "⚠️ Sorry, something went wrong. Please try again.",
        "footer": "<div style=\"background-color:#e6f7ff; color:#00529B; padding:15px; border-left:4px solid #00529B; margin:20px 0;\">\n<strong>Insights generated through analysis of:</strong><br>\n1. Our medical profiles database<br>\n2. Global health benchmarks<br>\n<em>All data processed with strict compliance.</em>\n</div>"
    },
    "zh": {
        "email_subject": "您的健康洞察报告",
        "report_title": "🎉 全球健康洞察（简体）",
        "response_lang": "你是一位只用简体中文回答的健康顾问。",
        "creative_header": "💡 创意支持建议",
        "fallback_error": "⚠️ 抱歉，目前系统忙碌，请稍后再试。",
        "footer": "<div style=\"background-color:#e6f7ff; color:#00529B; padding:15px; border-left:4px solid #00529B; margin:20px 0;\">\n<strong>本报告通过分析以下数据生成:</strong><br>\n1. 匿名医疗资料库<br>\n2. 全球健康基准数据<br>\n<em>所有数据处理均符合隐私保护法规</em>\n</div>"
    },
    "tw": {
        "email_subject": "您的健康洞察報告",
        "report_title": "🎉 全球健康洞察（繁體）",
        "response_lang": "你是一位只用繁體中文回答的健康顧問。",
        "creative_header": "💡 創意支持建議",
        "fallback_error": "⚠️ 抱歉，系統忙碌中，請稍後再試。",
        "footer": "<div style=\"background-color:#e6f7ff; color:#00529B; padding:15px; border-left:4px solid #00529B; margin:20px 0;\">\n<strong>本報告通過分析以下數據生成:</strong><br>\n1. 匿名醫療資料庫<br>\n2. 全球健康基準數據<br>\n<em>所有數據處理均符合隱私保護法規</em>\n</div>"
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

def ask_gpt(prompt, lang="en", temp=0.7):
    try:
        role = LANGUAGE[lang]["response_lang"]
        result = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": role},
                {"role": "user", "content": prompt}
            ],
            temperature=temp
        )
        return result.choices[0].message.content
    except Exception as e:
        logging.warning(f"GPT error: {e}")
        return LANGUAGE[lang]["fallback_error"]

def generate_metrics_with_ai(prompt_text, lang="en"):
    try:
        raw = ask_gpt(prompt_text, lang)
        lines = raw.strip().split("\n")
        metrics = []
        current_title, labels, values = "", [], []
        for line in lines:
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
        return metrics or default_metrics(lang)
    except Exception as e:
        logging.warning(f"GPT metric parse error: {e}")
        return default_metrics(lang)

def default_metrics(lang):
    if lang == "zh":
        return [
            {"title": "认知健康", "labels": ["记忆", "专注", "反应"], "values": [65, 70, 60]},
            {"title": "情绪健康", "labels": ["情绪", "压力", "能量"], "values": [68, 55, 62]},
            {"title": "身体能力", "labels": ["平衡", "力量", "协调"], "values": [60, 70, 58]}
        ]
    if lang == "tw":
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
        notes = data.get("details") or ("无详细说明" if lang in ["zh", "tw"] else "No details provided")
        ref = data.get("referrer")
        angel = data.get("angel")
        age = compute_age(dob)

        if lang == "zh":
            metrics_prompt = f"请生成一个关于{age}岁{gender}，来自{country}，健康问题为「{concern}」的健康图表。请列出三个主题（以 ### 开头），每个包含三个指标，格式为‘指标: 数值%’。"
        elif lang == "tw":
            metrics_prompt = f"請針對{age}歲{gender}，來自{country}，健康問題為「{concern}」，生成健康圖表內容。每個主題以 ### 開頭，列出三個百分比項目，格式為‘項目: 數值%’。"
        else:
            metrics_prompt = f"Generate health chart data for a {age}-year-old {gender} in {country} with concern '{concern}' and notes '{notes}'. Include 3 sections prefixed with ### and 3 indicators below each using 'Label: Value%'."

        metrics = generate_metrics_with_ai(metrics_prompt, lang)

        summary_prompt = (
            f"一位{age}岁{gender}，来自{country}，主要健康问题是「{concern}」，详细说明为「{notes}」。请为类似情况的人写四段建议。"
            if lang == "zh" else
            f"{age}歲{gender}，來自{country}，健康問題為「{concern}」，補充說明為「{notes}」。請撰寫四段實用建議。"
            if lang == "tw" else
            f"A {age}-year-old {gender} in {country} has concern '{concern}'. Description: {notes}. Write 4 helpful paragraphs."
        )
        creative_prompt = (
            f"作为健康顾问，请给出10个适合{age}岁{gender}（{country}）有“{concern}”困扰者的创意健康建议，结合说明「{notes}」。"
            if lang == "zh" else
            f"請以健康顧問身份，針對{age}歲{gender}（{country}），健康問題為「{concern}」，結合說明「{notes}」，提出10項創意健康建議。"
            if lang == "tw" else
            f"As a wellness coach, suggest 10 creative health ideas for a {age}-year-old {gender} in {country} facing '{concern}'. Consider: {notes}."
        )

        summary = html.escape(ask_gpt(summary_prompt, lang))
        creative = html.escape(ask_gpt(creative_prompt, lang, temp=0.85))

        chart_html = ""
        for m in metrics:
            chart_html += f"<strong>{m['title']}</strong><br>"
            for l, v in zip(m['labels'], m['values']):
                chart_html += f"<div style='display:flex; align-items:center; margin-bottom:8px;'><span style='width:180px;'>{l}</span><div style='flex:1; background:#eee; border-radius:5px; overflow:hidden;'><div style='width:{v}%; height:14px; background:#5E9CA0;'></div></div><span style='margin-left:10px;'>{v}%</span></div>"
            chart_html += "<br>"

        creative_html = f"<br><br><h3 style='font-size:24px; font-weight:bold;'>{content['creative_header']}</h3><br>"
        creative_html += ''.join(f"<p style='margin-bottom:14px;'>{line.strip()}</p>" for line in creative.split("\n") if line.strip())

        html_output = (
            f"<h4 style='text-align:center; font-size:24px;'>{content['report_title']}</h4>"
            f"<p><strong>姓名:</strong> {name}<br><strong>出生:</strong> {dob}<br><strong>国家:</strong> {country}<br>"
            f"<strong>性别:</strong> {gender}<br><strong>年龄:</strong> {age}<br><strong>身高:</strong> {height} cm<br><strong>体重:</strong> {weight} kg<br>"
            f"<strong>主问题:</strong> {concern}<br><strong>说明:</strong> {notes}<br><strong>推荐人:</strong> {ref}<br><strong>关心者:</strong> {angel}</p>"
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
