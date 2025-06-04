# -*- coding: utf-8 -*-
import random
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def generate_metrics():
    return [random.randint(35, 75) for _ in range(3)]

def generate_health_insight(age, country, concern, metrics):
    m1, m2, m3 = metrics

    if concern.lower() == "sleep quality and burnout":
        return f"""
<p style='line-height:1.7; font-size:16px; margin-bottom:16px;'>
In Singapore’s fast-moving work culture, many professionals in their {age}s face deeply disrupted rest. A <strong>Sleep Efficiency: {m1}%</strong> reflects not just lack of time — but broken cycles. Night scrolling, late work emails, and high coffee intake interrupt vital stages of sleep...
</p>
<p style='line-height:1.7; font-size:16px; margin-bottom:16px;'>
A <strong>Cortisol Rhythm: {m2}%</strong> reveals high stress activation. Even when resting, the body may be on high alert. Afternoon anxiety and sugar cravings are common, especially for those juggling professional goals and family expectations.
</p>
<p style='line-height:1.7; font-size:16px; margin-bottom:16px;'>
With a <strong>Recovery Index: {m3}%</strong>, the body struggles to rebuild cellular energy. Morning fog and emotional flatness become routine when restorative rest is sacrificed day after day. It's not a lack of effort, but an overflow of responsibility that drains deeply.
</p>
<p style='line-height:1.7; font-size:16px; margin-bottom:16px;'>
Recovery often begins with silence. Gentle stretching at dawn, lowered light exposure at night, and sacred sleep hours have helped many in their 40s reclaim deep rest — not as luxury, but as survival. 🛏️🌿
</p>
"""
    elif concern.lower() == "sensitive skin and redness":
        return f"""
<p style='line-height:1.7; font-size:16px; margin-bottom:16px;'>
At around {age}, many in Malaysia begin to notice their skin reacting more often — to heat, fabric, even emotions. A <strong>Hydration Level: {m1}%</strong> suggests skin cells aren’t holding moisture, often leading to stinging, itch, or dullness, especially under constant air-conditioning.
</p>
<p style='line-height:1.7; font-size:16px; margin-bottom:16px;'>
A <strong>Redness Index: {m2}%</strong> indicates reactive inflammation. It could be triggered by fabrics, sun, or harsh cleansers — common in fast-paced lifestyles where skincare is rushed or skipped. Stress-induced redness is also often overlooked in daily routines.
</p>
<p style='line-height:1.7; font-size:16px; margin-bottom:16px;'>
The <strong>Chemical Exposure: {m3}%</strong> shows overuse of whitening or exfoliating products. Many young adults unknowingly overload the skin barrier by layering too many active ingredients or using harsh detergents at home and work.
</p>
<p style='line-height:1.7; font-size:16px; margin-bottom:16px;'>
True skincare in this region means going minimal: aloe soaks, rice water rinses, shaded morning walks, and even natural oils like tamanu or moringa. The calmer the care, the louder the healing. 🍃
</p>
"""
    elif concern.lower() == "afternoon fatigue and bloating":
        return f"""
<p style='line-height:1.7; font-size:16px; margin-bottom:16px;'>
By age {age}, especially in fast-paced regions like Taiwan, digestion becomes more sensitive. A <strong>Digestive Rhythm: {m1}%</strong> signals the gut is off-track. Skipping breakfast or multitasking while eating affects absorption and energy flow by noon.
</p>
<p style='line-height:1.7; font-size:16px; margin-bottom:16px;'>
A <strong>Inflammation Index: {m2}%</strong> points to low-grade irritation. Tech stress, late dinners, and fried snacks are often culprits — with many suppressing early signs like bloating or heaviness until symptoms become daily discomfort.
</p>
<p style='line-height:1.7; font-size:16px; margin-bottom:16px;'>
The <strong>Vitality Level: {m3}%</strong> reflects a tired but functioning body. The 3PM crash isn’t laziness — it’s biology. When meals are rushed or digestion is weak, energy reserves fall dramatically and mood dips without warning.
</p>
<p style='line-height:1.7; font-size:16px; margin-bottom:16px;'>
Healing begins with rhythm. Warm soups, ginger compresses, or 10-minute foot soaks after dinner help many recalibrate digestion. Those in their 30s often find that healing comes not from medication, but mindful mealtime rituals. 🥣
</p>
"""
    elif concern.lower() == "hormonal imbalance and skin breakouts":
        return f"""
<p style='line-height:1.7; font-size:16px; margin-bottom:16px;'>
In tropical Singapore, hormonal swings often appear in the late 30s as adult acne, mood changes, or sudden skin flare-ups. A <strong>Hormonal Stability: {m1}%</strong> suggests irregular cycles or internal hormonal surges that are frequently missed in basic health checks.
</p>
<p style='line-height:1.7; font-size:16px; margin-bottom:16px;'>
A <strong>Detox Pathways: {m2}%</strong> hints at liver and kidney systems working overtime — possibly overloaded by processed food, sleep debt, stimulants, or medication. Many adults carry this silently, unaware of internal buildup.
</p>
<p style='line-height:1.7; font-size:16px; margin-bottom:16px;'>
The <strong>Skin Barrier: {m3}%</strong> shows the skin is fragile, reactive, and easily inflamed. When hormonal balance is off, even trusted products may sting or cause redness. Flare-ups around the chin or jawline are especially common during this life stage.
</p>
<p style='line-height:1.7; font-size:16px; margin-bottom:16px;'>
Balance is found not in treatment but in trust. Nourishing soups, maca tea, liver-friendly herbs, digital breaks, and even magnesium soaks can restore inner calm. Skin often reflects emotional peace, not just product use. 🌿💧
</p>
"""
    else:
        return "<p style='line-height:1.7;'>Concern not recognized. Please check input.</p>"

@app.route("/health_insight", methods=["POST"])
def health_insight():
    data = request.json
    age = data.get("age", 40)
    country = data.get("country", "Singapore")
    concern = data.get("concern", "Sleep Quality and Burnout")
    metrics = data.get("metrics", generate_metrics())
    summary = generate_health_insight(age, country, concern, metrics)
    return jsonify({"summary": summary})
