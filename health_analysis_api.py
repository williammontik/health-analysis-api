# -*- coding: utf-8 -*-
import os, logging, smtplib, traceback, re
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

# --- ENGLISH LANGUAGE DATA ---
LABELS = {
    "name": "Full Name", "chinese_name": "Chinese Name", "dob": "Date of Birth", "country": "Country", "gender": "Gender",
    "age": "Age", "height": "Height (cm)", "weight": "Weight (kg)", "concern": "Main Concern",
    "desc": "Additional Details", "ref": "Referrer", "angel": "Wellness Pal",
    "summary_title": "🧠 Summary:", "suggestions_title": "💡 Creative Suggestions:",
    "metrics_title": "📈 Health Metrics Breakdown:",
    "submitted_info": "📌 Submitted Info:",
    "disclaimer_title": "🛡️ Disclaimer:",
    "disclaimer_text": "🩺 This platform offers general lifestyle suggestions. Please consult a licensed medical professional for diagnosis or treatment decisions."
}
EMAIL_SUBJECT = "Your Health Insight Report"

def build_summary_prompt(age, gender, country, concern, notes, metrics):
    metric_lines = [f"{label}: {value}%" for block in metrics for label, value in zip(block["labels"], block["values"])]
    metrics_summary = ", ".join(metric_lines[:9])

    return (
        f"Analyze the health profile of a {age}-year-old {gender} from {country} with a primary concern of '{concern}'. Notes: '{notes}'. "
        f"Craft a comprehensive, 4-paragraph narrative summary in English based on these key metrics: {metrics_summary}. "
        f"Instructions for the summary:\n"
        f"1.  **Tone & Style:** Adopt the persona of an expert, empathetic health analyst. The tone must be insightful and encouraging, not clinical or robotic. Weave the data into a holistic story.\n"
        f"2.  **Content Depth:** Don't just list the numbers. Explain the significance and logical connections. For example, connect a metric like 'Processed food intake at 70%' to the concern of '{concern}'. Explain *how* these factors are often related for this demographic.\n"
        f"3.  **Group Phrasing Only:** Strictly avoid personal pronouns (you, your, their). Use phrases like 'For individuals in this age group...', 'This profile often suggests...'.\n"
        f"4.  **Structure:** Ensure the output is exactly 4 distinct paragraphs, each rich in content and providing a coherent insight."
    )

def build_suggestions_prompt(age, gender, country, concern, notes):
    return (
        f"Suggest 10 specific and gentle lifestyle improvements in English for a {age}-year-old {gender} from {country} experiencing '{concern}'. "
        f"Use a warm, supportive tone and include helpful emojis. The suggestions should be practical and culturally appropriate. "
        f"⚠️ Do not use names or personal pronouns (she/her/he/his). Only use group phrasing like 'individuals facing this concern'."
    )

def compute_age(dob_year):
    try:
        return datetime.now().year - int(dob_year)
    except (ValueError, TypeError):
        return 0

def get_openai_response(prompt, temp=0.75):
    try:
        result = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=temp
        )
        return result.choices[0].message.content
    except Exception as e:
        logging.error(f"OpenAI error: {e}")
        return "⚠️ Unable to generate AI response."

def generate_metrics_with_ai(prompt):
    try:
        content = get_openai_response(prompt)
        lines = content.strip().split("\n")
        metrics, current_title, labels, values = [], "", [], []
        for line in lines:
            if line.startswith("###"):
                if current_title: metrics.append({"title": current_title, "labels": labels, "values": values})
                current_title = line.replace("###", "").strip()
                labels, values = [], []
            elif ":" in line:
                try:
                    label, val = line.split(":", 1)
                    labels.append(label.strip())
                    values.append(int(re.sub(r'[^\d]', '', val)))
                except (ValueError, IndexError): continue
        if current_title: metrics.append({"title": current_title, "labels": labels, "values": values})
        return metrics if metrics else [{"title": "Default Metrics", "labels": ["Data Point A", "Data Point B", "Data Point C"], "values": [65,75,85]}]
    except Exception as e:
        logging.error(f"Chart parse error: {e}")
        return [{"title": "Error Generating Metrics", "labels": ["Please check server logs"], "values": [50]}]

def send_email_notification(html_body):
    msg = MIMEText(html_body, 'html', 'utf-8')
    msg['Subject'] = EMAIL_SUBJECT
    msg['From'] = SMTP_USERNAME
    msg['To'] = SMTP_USERNAME
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        logging.error(f"Email send error: {e}")

@app.route("/health_analyze", methods=["POST"])
def health_analyze():
    try:
        data = request.get_json(force=True)
        age = compute_age(data.get("dob_year"))

        chart_prompt = (
            f"A {age}-year-old {data.get('gender')} from {data.get('country')} has a health concern: '{data.get('condition')}' "
            f"with these notes: '{data.get('details', 'N/A')}'. Generate 3 distinct health metric categories for this profile. "
            f"Each category must start with '###' and have exactly 3 unique, relevant metrics formatted as 'Metric Name: Value%'. "
            f"Values must be between 25-90. Respond with only the formatted blocks."
        )
        metrics = generate_metrics_with_ai(chart_prompt)

        summary_prompt = build_summary_prompt(age, data.get('gender'), data.get('country'), data.get('condition'), data.get('details'), metrics)
        summary = get_openai_response(summary_prompt)

        suggestions_prompt = build_suggestions_prompt(age, data.get('gender'), data.get('country'), data.get('condition'), data.get('details'))
        creative = get_openai_response(suggestions_prompt, temp=0.85)

        # Build HTML response with proper paragraph formatting
        summary_paragraphs = [p.strip() for p in summary.split('\n') if p.strip()]
        html_result = f"<div style='font-size:24px; font-weight:bold; margin-top:30px;'>{LABELS['summary_title']}</div><br>"
        html_result += ''.join(f"<p style='line-height:1.7; font-size:16px; margin-bottom:16px;'>{p}</p>" for p in summary_paragraphs)
        
        html_result += f"<div style='font-size:24px; font-weight:bold; margin-top:30px;'>{LABELS['suggestions_title']}</div><br>"
        html_result += ''.join(f"<p style='margin:16px 0; font-size:17px;'>{line}</p>" for line in creative.split("\n") if line.strip())

        html_result += f"<div style='font-size:18px; font-weight:bold; margin-top:40px;'>{LABELS['disclaimer_title']}</div>"
        html_result += f"<p style='font-size:15px; line-height:1.6;'>{LABELS['disclaimer_text']}</p>"

        # Optional: Build and send a comprehensive email notification
        # email_body = "..." 
        # send_email_notification(email_body)

        return jsonify({"metrics": metrics, "html_result": html_result})

    except Exception as e:
        logging.error(f"Health analyze error: {e}")
        traceback.print_exc()
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 5003)), host="0.0.0.0")
