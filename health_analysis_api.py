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
        "email_subject": "您的健康洞察報告",
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
            f"一名{age}歲的{gender}來自{country}，健康問題為「{concern}」，描述如下：{notes}。"
            f"請撰寫4段建議，不要用「你」，要像是給其他人建議。",
        "creative": lambda age, gender, country, concern, notes:
            f"請以健康教練的身份，為{country}一位{age}歲的{gender}，健康問題為「{concern}」的人，"
            f"提供10個創意建議。請根據這些描述：{notes}。"
    },
    "zh": {
        "summary": lambda age, gender, country, concern, notes:
            f"一位{age}歲、性別為{gender}、來自{country}的人，有健康問題「{concern}」。說明如下：{notes}。"
            f"請寫4段建議，幫助其他有相似情況的人。請避免直接使用“你”來稱呼。",
        "creative": lambda age, gender, country, concern, notes:
            f"作為一名健康教練，請為{country}一位{age}歲的{gender}，面臨「{concern}」問題的人，提供10條創意健康建議。"
            f"請參考以下描述：{notes}。"
    },
    "en": {
        "summary": lambda age, gender, country, concern, notes:
            f"A {age}-year-old {gender} in {country} has concern '{concern}'. Description: {notes}. "
            f"Write 4 helpful paragraphs for similar individuals. Do not address directly.",
        "creative": lambda age, gender, country, concern, notes:
            f"As a wellness coach, suggest 10 creative health ideas for someone in {country}, aged {age}, gender {gender}, with '{concern}'. "
            f"Take into account: {notes}."
    }
}

chart_prompts = {
    "tw": lambda age, gender, country, concern, notes:
        f"請為{country}一位{age}歲的{gender}產生健康圖表資料，主要問題是「{concern}」，補充說明為：{notes}。"
        f"請用 ### 開頭的標題分為3類，並為每類列出3項指標，格式為「指標: 數值%」。",
    "zh": lambda age, gender, country, concern, notes:
        f"請為{country}一位{age}歲的{gender}生成健康圖表資料，問題為「{concern}」，補充說明：{notes}。"
        f"請用 ### 開頭的分類標題，共3類，並為每類列出3個指標，格式為“項目: 數值%”。",
    "en": lambda age, gender, country, concern, notes:
        f"Generate health chart data for a {age}-year-old {gender} in {country} with concern '{concern}' and notes '{notes}'. "
        f"Include 3 sections prefixed with ### title, and 3 indicators below each using format 'Label: Value%'."
}
