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

def build_messages(lang, user_prompt):
    system_msg = {
        "en": "Please respond entirely in English.",
        "zh": "请确保以下所有回答都使用简体中文，不要使用英文。",
        "tw": "請確保以下所有回答都使用繁體中文，請勿使用英文。"
    }.get(lang, "Please respond in English.")

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_prompt}
    ]

# ✅ Patch OpenAI call functions to use language control

def get_openai_response(prompt, lang, temp=0.7):
    try:
        result = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=build_messages(lang, prompt),
            temperature=temp
        )
        return result.choices[0].message.content
    except Exception as e:
        app.logger.error(f"OpenAI error: {e}")
        return "⚠️ Unable to generate content."

def generate_metrics_with_ai(prompt_text, lang):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=build_messages(lang, prompt_text),
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
            metrics.append({"title": current_title, "labels": labels, "values": values})
        if not metrics:
            raise ValueError("GPT returned no metrics.")
        return metrics
    except Exception as e:
        logging.warning(f"GPT metric error: {e}")
        return []  # or fallback values
