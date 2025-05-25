# -*- coding: utf-8 -*-
import os
from datetime import datetime
from dateutil import parser
from flask import Flask, request, jsonify
from flask_cors import CORS
import openai  # make sure openai is installed

app = Flask(__name__)
CORS(app)

openai.api_key = os.getenv("OPENAI_API_KEY")

PROMPTS = {
    "en": {
        "summary": lambda age, gender, country, concern, notes:
            f"Summarize the current situation of a {age}-year-old {gender} from {country} facing '{concern}'. Include general trends, lifestyle relevance, and statistics if possible. Avoid using 'you'.",
        "creative": lambda age, gender, country, concern, notes:
            f"Suggest 10 short, creative, and actionable lifestyle tips for a {age}-year-old {gender} from {country} dealing with '{concern}'. "
            f"Format: use one emoji and 5–10 words per tip. Include % effectiveness or relevance where appropriate. No introduction needed, just list."
    }
}

def compute_age(dob):
    try:
        dt = parser.parse(dob)
        today = datetime.today()
        return today.year - dt.year - ((today.month, today.day) < (dt.month, dt.day))
    except:
        return 0

def get_openai_response(prompt, temp=0.7):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=temp
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error generating content: {e}"

@app.route("/health_summary_test", methods=["POST"])
def health_summary_test():
    try:
        data = request.get_json(force=True)
        lang = data.get("lang", "en")
        prompts = PROMPTS.get(lang, PROMPTS["en"])

        age = compute_age(data["dob"])
        gender = data["gender"]
        country = data["country"]
        concern = data["condition"]
        notes = data.get("details", "No extra notes.")

        summary_prompt = prompts["summary"](age, gender, country, concern, notes)
        creative_prompt = prompts["creative"](age, gender, country, concern, notes)

        summary = get_openai_response(summary_prompt)
        creative = get_openai_response(creative_prompt, temp=0.85)

        summary_html = f"<h3>🧠 Summary:</h3><p>{summary}</p>"
        creative_html = "<h3>💡 Creative Suggestions:</h3><ul>" + \
            "".join(f"<li>{line.strip()}</li>" for line in creative.split("\n") if line.strip()) + "</ul>"
        disclaimer_html = "<h3>🛡️ Disclaimer:</h3><p>🩺 This platform offers general lifestyle suggestions. Please consult a licensed medical professional for diagnosis or treatment decisions.</p>"

        return jsonify({
            "summary": summary_html,
            "creative": creative_html,
            "disclaimer": disclaimer_html
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
