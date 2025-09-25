from flask import Flask, render_template_string, request, redirect, url_for, session
import os, json
from dotenv import load_dotenv
import stripe
import random

load_dotenv()  # 读取 .env

STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")

stripe.api_key = STRIPE_SECRET_KEY
if not STRIPE_SECRET_KEY:
    raise ValueError("❌ Stripe Secret Key 没有加载成功，请检查 .env 文件！")
else:
    print("✅ Stripe Secret Key 已加载:", STRIPE_SECRET_KEY[:8] + "...")

app = Flask(__name__)
app.secret_key = os.urandom(24)

# 读取多语言文件
with open("lang.json","r",encoding="utf-8") as f:
    LANG_DATA = json.load(f)

BASE_CSS_JS = """
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<style>
body {font-family: Arial, sans-serif; background:#f2f2f2; text-align:center; padding:20px;}
.card {background:white; padding:20px; margin:auto; max-width:600px; width:95%; border-radius:10px; box-shadow:0 2px 10px rgba(0,0,0,0.1); opacity:1; transition:opacity 0.3s;}
button.option-btn, button.start-btn {padding:15px 20px; margin:10px 0; border:none; border-radius:5px; background:#eee; cursor:pointer; font-size:16px; display:block; width:100%; transition: all 0.2s;}
button.option-btn:hover, button.start-btn:hover {background:#ddd;}
button.option-btn.selected {background:#4CAF50; color:white; transform: scale(1.03);}
.progress {background:#ddd; border-radius:5px; overflow:hidden; margin-bottom:15px; height:20px;}
.progress-bar {height:20px; background:#4CAF50; width:0%; transition: width 0.3s;}
@media (max-width: 600px){.card{padding:15px;} button.option-btn, button.start-btn{font-size:14px;}}
</style>
<script>
function selectOption(btn, answer){
    let buttons = document.querySelectorAll(".option-btn");
    buttons.forEach(b=>b.classList.remove("selected"));
    btn.classList.add("selected");
    setTimeout(function(){window.location.href="?answer="+encodeURIComponent(answer);},200);
}
function fadeOutCard(callback){
    let card = document.querySelector(".card");
    card.style.opacity = 0;
    setTimeout(callback,200);
}
window.onload = function(){
    let progress = document.querySelector(".progress-bar");
    if(progress){ progress.style.width = progress.getAttribute("data-percent") + "%"; }
}
function startCountdown(){
    let countdownDiv = document.getElementById("countdown");
    let count = 3;
    countdownDiv.innerHTML = lang_data.starting+"："+count+"秒";
    let interval = setInterval(function(){
        count -= 1;
        if(count>0){ countdownDiv.innerHTML = lang_data.starting+"："+count+"秒"; }
        else{
            clearInterval(interval);
            window.location.href = "/quiz";
        }
    },1000);
}
</script>
"""

def get_lang():
    lang = request.accept_languages.best_match(['zh','en','ja'])
    if not lang:
        lang = 'en'
    return lang

@app.route("/")
def start():
    lang = get_lang()
    text = LANG_DATA[lang]
    html = f"""
    {BASE_CSS_JS}
    <script>var lang_data={json.dumps(text)};</script>
    <div class='card'>
        <h2>{text['start_title']}</h2>
        <p>{text['start_desc'].format(total=len(LANG_DATA[lang]['questions']))}</p>
        <button class='start-btn' onclick='startCountdown()'>{text['start_btn']}</button>
        <p id="countdown" style="font-size:18px; color:#555;"></p>
    </div>
    """
    return render_template_string(html)

@app.route("/quiz/restart")
def quiz_restart():
    session.pop('current_index', None)
    session.pop('answers', None)
    session.pop('shuffled_questions', None)
    return redirect(url_for('quiz'))

@app.route("/quiz")
def quiz():
    lang = get_lang()
    text = LANG_DATA[lang]

    # 空题库保护
    if 'current_index' not in session or 'shuffled_questions' not in session:
        session['current_index'] = 0
        session['answers'] = []
        session['shuffled_questions'] = random.sample(text['questions'], len(text['questions']))

    questions_shuffled = session['shuffled_questions']
    if not questions_shuffled:
        return "❌ 当前题库为空，请检查 lang.json"

    idx = session['current_index']
    ans = request.args.get("answer")
    if ans:
        session['answers'].append(ans)
        session['current_index'] += 1
        idx = session['current_index']
        if idx >= len(questions_shuffled):
            return redirect(url_for("checkout"))

    if idx < len(questions_shuffled):
        q = questions_shuffled[idx]
        total = len(questions_shuffled)
        progress_percent = int((idx / total) * 100)
        html = f"""
        {BASE_CSS_JS}
        <script>var lang_data={json.dumps(text)};</script>
        <div class='card' id='card'>
            <h2>{text['quiz_title']}</h2>
            <div class='progress'><div class='progress-bar' data-percent='{progress_percent}'></div></div>
            <p>{text['quiz_progress'].format(current=idx+1,total=total)}</p>
            <p>{q['q']}</p>
        """
        for opt_text, val in q['options'].items():
            html += f"<button class='option-btn' onclick=\"fadeOutCard(()=>selectOption(this,'{val}'))\">{opt_text}</button>"
        html += "</div>"
        return render_template_string(html)

@app.route("/checkout")
def checkout():
    lang = get_lang()
    text = LANG_DATA[lang]
    try:
        session_stripe = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'jpy',
                    'product_data': {'name': 'MBTI 测试'},
                    'unit_amount': 1000,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url="https://mbti-flask-5yrr.onrender.com/success?status=success",
            cancel_url="https://mbti-flask-5yrr.onrender.com/success?status=fail",
        )
    except Exception as e:
        return str(e)

    html = f"""
    {BASE_CSS_JS}
    <div class="card">
        <h2>{text['checkout_title']}</h2>
        <h3>Stripe 信用卡支付</h3>
        <p>{text['checkout_desc_stripe'].format(amount=1000)}</p>
        <a href="{session_stripe.url}"><button>{text['checkout_btn_stripe']}</button></a>
        <p style="margin-top:20px;"><a href="{url_for('quiz_restart')}">{text['quiz_restart']}</a></p>
    </div>
    """
    return render_template_string(html)

@app.route("/payment_failed")
def payment_failed():
    lang = get_lang()
    text = LANG_DATA[lang]
    html = f"""
    {BASE_CSS_JS}
    <div class='card'>
        <h2>{text['payment_failed_title']}</h2>
        <p>{text['payment_failed_desc']}</p>
        <a href="{url_for('checkout')}"><button>{text['payment_failed_btn']}</button></a>
    </div>
    """
    return render_template_string(html)

@app.route("/success")
def success():
    lang = get_lang()
    text = LANG_DATA[lang]
    payment_status = request.args.get("status", "success")
    if payment_status != "success":
        return render_template_string(f"""
        {BASE_CSS_JS}
        <div class='card'>
            <h2>{text['payment_failed_title']}</h2>
            <p>{text['payment_failed_desc']}</p>
            <a href="{url_for('checkout')}"><button>{text['payment_failed_btn']}</button></a>
        </div>
        """)

    answers = session.get('answers')
    if not answers:
        return redirect(url_for("quiz_restart"))

    scores = {"E":0,"I":0,"N":0,"S":0,"T":0,"F":0,"J":0,"P":0}
    for ans in answers:
        if ans in scores: scores[ans]+=1
        elif ans=="E/I": scores["E"]+=0.7; scores["I"]+=0.3
        elif ans=="I/E": scores["I"]+=0.7; scores["E"]+=0.3
        elif ans=="T/F": scores["T"]+=0.7; scores["F"]+=0.3
        elif ans=="F/T": scores["F"]+=0.7; scores["T"]+=0.3
        elif ans=="N/S": scores["N"]+=0.7; scores["S"]+=0.3
        elif ans=="S/N": scores["S"]+=0.7; scores["N"]+=0.3
        elif ans=="J/P": scores["J"]+=0.7; scores["P"]+=0.3
        elif ans=="P/J": scores["P"]+=0.7; scores["J"]+=0.3

    result_type = ""
    result_type += "E" if scores["E"]>=scores["I"] else "I"
    result_type += "N" if scores["N"]>=scores["S"] else "S"
    result_type += "T" if scores["T"]>=scores["F"] else "F"
    result_type += "J" if scores["J"]>=scores["P"] else "P"

    description = text['results'].get(result_type,"暂无描述")

    session.pop('current_index',None)
    session.pop('answers',None)
    session.pop('shuffled_questions',None)

    html = f"""
    {BASE_CSS_JS}
    <div class='card'>
        <h2>{text['success_title']}</h2>
        <p>{text['success_type'].format(result=result_type)}</p>
        <p>{description}</p>
        <a href="{url_for('quiz_restart')}"><button>{text['success_btn']}</button></a>
    </div>
    """
    return render_template_string(html)

if __name__=="__main__":
    app.run(debug=True)
