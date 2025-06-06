<!-- === START HEALTH WIDGET (ENGLISH, FINAL VERSION) === -->

<!-- 1) Styles -->
<style>
  @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
  #hiddenFormHealth { opacity: 0; transform: translateY(20px); transition: opacity .5s, transform .5s; display: none; }
  #hiddenFormHealth.show { opacity: 1; transform: translateY(0); }
  #resultContainerHealth { opacity: 0; transition: opacity .5s; display: none; }
  #resultContainerHealth.show { opacity: 1; display: block; }
  #resultContainerHealth, #resultContainerHealth * { font-family: sans-serif; font-size: 16px; }
  .dob-group { display: flex; gap: 10px; }
  .dob-group select { flex: 1; }
</style>

<!-- 2) Chart.js -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<!-- 3) Next Button -->
<button id="simulateHealthButton" type="button" style="padding:10px 20px;background:#4CAF50;color:#fff;border:none;border-radius:8px;cursor:pointer;display:none;">
  Next
</button>

<!-- 4) Hidden Form -->
<div id="hiddenFormHealth">
  <div style="background:#f9f9f9;padding:20px;border-left:6px solid #4CAF50;border-radius:8px;margin:20px 0;">
    <p style="font-size:18px;font-weight:bold;color:#4CAF50;">🌱 Let’s explore how your health data can unlock new insights.</p>
    <p style="margin-top:10px;font-size:15px;line-height:1.7;color:#333;">
      Please fill out the details below. Our system will benchmark your profile against similar individuals to provide meaningful wellness insights.
    </p>
    <ul style="font-size:15px;line-height:1.7;padding-left:20px;color:#333;">
      <li>📊 <strong>Wellness chart:</strong> Based on lifestyle patterns and demographics</li>
      <li>🧠 <strong>Strategic summary:</strong> AI-generated guidance with tips</li>
      <li>✅ <strong>PDPA Consent:</strong> Required to begin</li>
    </ul>
    <p style="margin-top:10px;font-size:15px;line-height:1.7;color:#333;">
      Your data is kept confidential and used solely for personalized analysis. 🛡️
    </p>
  </div>

  <div style="margin-bottom:20px;display:flex;align-items:center;">
    <input type="checkbox" id="pdpaCheckboxHealth" style="margin-right:10px;">
    <label for="pdpaCheckboxHealth">
      I consent to submit my personal data according to PDPA regulations in Singapore, Malaysia, and Taiwan.
    </label>
  </div>

  <form id="healthForm" style="display:flex;flex-direction:column;gap:15px;pointer-events:none;opacity:0.3;">
    <input type="hidden" name="lang" value="en">
    <label>👤 Full Name</label>
    <input type="text" id="name" required disabled>
    <label>🗓️ Date of Birth</label>
    <div class="dob-group">
      <select id="dob_day" disabled required><option value="">Day</option></select>
      <select id="dob_month" disabled required>
        <option value="">Month</option>
        <option value="1">Jan</option><option value="2">Feb</option><option value="3">Mar</option>
        <option value="4">Apr</option><option value="5">May</option><option value="6">Jun</option>
        <option value="7">Jul</option><option value="8">Aug</option><option value="9">Sep</option>
        <option value="10">Oct</option><option value="11">Nov</option><option value="12">Dec</option>
      </select>
      <select id="dob_year" disabled required><option value="">Year</option></select>
    </div>
    <label>⚧️ Gender</label>
    <select id="gender" required disabled><option value="">Please Select</option><option>Male</option><option>Female</option></select>
    <label>📏 Height (cm)</label>
    <input type="number" id="height" required disabled>
    <label>⚖️ Weight (kg)</label>
    <input type="number" id="weight" required disabled>
    <label>🌍 Country</label>
    <select id="country" required disabled><option value="">Please Select</option><option>Singapore</option><option>Malaysia</option><option>Taiwan</option></select>
    <label>📌 Main Concern</label>
    <select id="condition" required disabled><option value="">Please select</option><option>High Blood Pressure</option><option>Low Blood Pressure</option><option>Diabetes</option><option>High Cholesterol</option><option>Skin Problem</option><option>Other</option></select>
    <label>📄 Additional Details</label>
    <textarea id="details" maxlength="300" required disabled></textarea>
    <label>🤜 Referrer (if any)</label>
    <input type="text" id="referrer" disabled>
    <label>🪨 Wellness Pal (optional)</label>
    <input type="text" id="angel" disabled>
    <button type="submit" id="submitButtonHealth" style="padding:14px;background:#4CAF50;color:#fff;border:none;border-radius:10px;cursor:pointer;" disabled>🚀 Submit</button>
  </form>
</div>

<!-- 5) Spinner + Results -->
<div id="loadingMessageHealth" style="display:none;text-align:center;margin-top:30px;">
  <div style="width:60px;height:60px;border:6px solid #ccc;border-top:6px solid #4CAF50;border-radius:50%;animation:spin 1s linear infinite;margin:0 auto;"></div>
  <p style="color:#4CAF50;margin-top:10px;">🔄 AI is analyzing, please wait…</p>
</div>
<div id="resultContainerHealth"></div>

<!-- 6) Reset Button -->
<div id="resetContainerHealth" style="text-align:center; margin-top:20px; display:none;">
  <button id="resetButtonHealth" style="padding:14px; background:#2196F3; color:#fff; border:none; border-radius:10px; cursor:pointer;">
    🔄 Reset
  </button>
</div>

<!-- 7) Script -->
<script>
  document.addEventListener('DOMContentLoaded', () => {
    const nextBtn = document.getElementById('simulateHealthButton');
    const formWrapper = document.getElementById('hiddenFormHealth');
    const pdpa = document.getElementById('pdpaCheckboxHealth');
    const form = document.getElementById('healthForm');
    const spinner = document.getElementById('loadingMessageHealth');
    const resultDiv = document.getElementById('resultContainerHealth');
    const resetContainer = document.getElementById('resetButtonHealth').parentElement;

    setTimeout(() => { nextBtn.style.display = 'inline-block'; }, 5000);

    for (let i = 1; i <= 31; i++) {
      const opt = document.createElement('option');
      opt.value = i; opt.text = i;
      document.getElementById('dob_day').appendChild(opt);
    }
    const currentYear = new Date().getFullYear();
    for (let y = currentYear; y >= 1920; y--) {
      const opt = document.createElement('option');
      opt.value = y; opt.text = y;
      document.getElementById('dob_year').appendChild(opt);
    }

    nextBtn.addEventListener('click', () => {
      formWrapper.style.display = 'block';
      setTimeout(() => { formWrapper.classList.add('show'); }, 10);
    });

    pdpa.addEventListener('change', () => {
      const enabled = pdpa.checked;
      form.querySelectorAll('input, select, textarea, button').forEach(el => el.disabled = !enabled);
      form.style.opacity = enabled ? '1' : '0.3';
      form.style.pointerEvents = enabled ? 'auto' : 'none';
    });

    form.addEventListener('submit', async e => {
      e.preventDefault();
      spinner.style.display = 'block';
      resultDiv.style.display = 'none';
      resultDiv.classList.remove('show');
      resultDiv.innerHTML = '';

      const payload = {
        lang: 'en',
        name: document.getElementById('name').value.trim(),
        dob_day: document.getElementById('dob_day').value,
        dob_month: document.getElementById('dob_month').value,
        dob_year: document.getElementById('dob_year').value,
        gender: document.getElementById('gender').value,
        height: document.getElementById('height').value,
        weight: document.getElementById('weight').value,
        country: document.getElementById('country').value,
        condition: document.getElementById('condition').value,
        details: document.getElementById('details').value,
        referrer: document.getElementById('referrer').value,
        angel: document.getElementById('angel').value
      };

      try {
        const res = await fetch('https://health-analysis-api.onrender.com/health_analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        const data = await res.json();
        spinner.style.display = 'none';
        resultDiv.style.display = 'block';
        resultDiv.classList.add('show');

        if (data.html_result) {
          const resultContent = document.createElement('div');
          resultContent.innerHTML = data.html_result;
          resultDiv.appendChild(resultContent);

          const insightNote = document.createElement('div');
          insightNote.innerHTML = `
            <div style="margin-top:30px;padding:20px;background:#f0f0f0;border-left:6px solid #4CAF50;border-radius:8px;line-height:1.7;">
              <strong style="font-size:18px;">📊 Insights Generated by KataChat AI</strong>
              <p style="margin-top:10px;">This wellness report is generated using KataChat’s proprietary AI models, based on:</p>
              <ul style="margin:10px 0 10px 20px;padding:0;">
                <li>A secure database of anonymized health and lifestyle profiles from individuals across Singapore, Malaysia, and Taiwan</li>
                <li>Aggregated global wellness benchmarks and behavioral trend data from trusted OpenAI research datasets</li>
              </ul>
              <p>All analysis complies strictly with PDPA regulations to protect your personal data while uncovering meaningful health insights.</p>
              <p style="color:#666;margin-top:10px;"><strong>🛡️ Note: This report is not a medical diagnosis. For any serious health concerns, please consult a licensed healthcare professional.</strong></p>
              <p style="margin-top:10px;">📬 <strong>PS:</strong> A personalized report will also be sent to your email and should arrive within 24–48 hours. If you'd like to explore the findings in more detail, we’d be happy to arrange a short 15-minute call.</p>
            </div>
          `;
          resultDiv.appendChild(insightNote);

          form.querySelectorAll('input, select, textarea, button').forEach(el => el.disabled = true);
          form.style.opacity = '0.3';
          form.style.pointerEvents = 'none';
          resetContainer.style.display = 'block';
        } else {
          resultDiv.innerHTML = '<p style="color:red;">⚠️ Unable to generate analysis. Please try again later.</p>';
        }
      } catch (err) {
        console.error(err);
        spinner.style.display = 'none';
        resultDiv.style.display = 'block';
        resultDiv.innerText = '⚠️ An error occurred — check the console.';
      }
    });

    document.getElementById('resetButtonHealth').addEventListener('click', () => {
      window.location.href = "https://katachat.online";
    });
  });
</script>

<!-- === END HEALTH WIDGET (ENGLISH, FINAL) === -->
