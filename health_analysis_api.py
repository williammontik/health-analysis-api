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

# Language definitions (unchanged)
LANGUAGE = {
  ...
}

# Email sender (unchanged)
def send_email(html_body, lang):
  ...

# Compute age (unchanged)
def compute_age(dob):
  ...

# Force GPT reply in Chinese if needed
def get_openai_response(prompt, temp=0.7):
    try:
        is_zh = '简体中文' in prompt or '繁體' in prompt or '請使用' in prompt
        result = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一位只用中文回答的健康助理。" if is_zh else "You are a helpful assistant replying in English."},
                {"role": "user", "content": prompt}
            ],
            temperature=temp
        )
        return result.choices[0].message.content
    except Exception as e:
        app.logger.error(f"OpenAI error: {e}")
        return "⚠️ 無法生成內容。"

# Force GPT to return chart metrics in Chinese
def generate_metrics_with_ai(prompt_text):
    try:
        is_zh = '简体中文' in prompt_text or '繁體' in prompt_text or '請使用' in prompt_text
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一位只用中文回答的健康助理。" if is_zh else "You are a helpful assistant replying in English."},
                {"role": "user", "content": prompt_text}
            ],
            temperature=0.7
        )
        lines = response.choices[0].message.content.strip().split("\n")
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
                try:
                    values.append(int(val.strip().replace("%", "")))
                except:
                    values.append(50)
        if current_title and labels and values:
            metrics.append({"title": current_title, "labels": labels, "values": values})
        return metrics
    except Exception as e:
        logging.warning(f"GPT metric error: {e}")
        return []

# Main API endpoint
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
        notes    = data.get("details") or "No additional description provided."
        ref      = data.get("referrer")
        angel    = data.get("angel")
        age      = compute_age(dob)

        if lang in ("zh", "tw"):
            gender = "男性" if gender == "男" else "女性" if gender == "女" else gender

        if lang == "zh":
            metrics_prompt = (
                f"请以中文回答。假设一位{age}岁的{gender}，来自{country}，主要健康问题是「{concern}」，补充描述为「{notes}」。"
                f"请生成健康图表数据，包含3个部分（以 ### 开头的中文标题），每个部分下列出3项指标（格式为：项目名称: 数值%）。"
            )
            summary_prompt = f"这是一位{age}岁的{gender}，来自{country}，健康问题是「{concern}」，补充说明：「{notes}」。请撰写四段说明，不要直接称呼对方。请使用简体中文。"
            creative_prompt = f"作为健康顾问，请针对{age}岁、性别{gender}、居住在{country}、健康问题是「{concern}」的人，结合「{notes}」提供10个创意健康建议。请使用简体中文。"
        elif lang == "tw":
            metrics_prompt = (
                f"請以繁體中文回答。假設一位{age}歲的{gender}，來自{country}，主要健康問題是「{concern}」，補充說明為「{notes}」。"
                f"請產生健康圖表資料，分為3個主題（每個以 ### 開頭，使用繁體中文），每個主題列出3個指標（格式為：項目名稱: 百分比%）。"
            )
            summary_prompt = f"這是一位{age}歲的{gender}，來自{country}，健康問題是「{concern}」，補充說明：「{notes}」。請撰寫四段內容，不要直接稱呼對方。請使用繁體中文。"
            creative_prompt = f"請以健康顧問身份，針對{age}歲的{gender}，來自{country}，健康問題為「{concern}」，結合補充說明「{notes}」，提供10項創意健康建議。請使用繁體中文。"
        else:
            metrics_prompt = f"Generate health chart data for a {age}-year-old {gender} in {country} with concern '{concern}' and notes '{notes}'. Include 3 sections prefixed with ### title, and 3 indicators below each using format 'Label: Value%'."
            summary_prompt = f"A {age}-year-old {gender} in {country} has concern '{concern}'. Description: {notes}. Write 4 helpful paragraphs for similar individuals. Do not address directly."
            creative_prompt = f"As a wellness coach, suggest 10 creative health ideas for someone in {country}, aged {age}, gender {gender}, with '{concern}'. Take into account: {notes}."

        metrics = generate_metrics_with_ai(metrics_prompt)
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

        creative_html = f"<br><br><h3 style='font-size:24px; font-weight:bold;'>{content['creative_title']}</h3><br>"
        creative_html += "".join(
            f"<p style='margin-bottom:14px;'>{line.strip()}</p>"
            for line in creative.split("\n") if line.strip()
        )
        creative_html += "<br>"

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
