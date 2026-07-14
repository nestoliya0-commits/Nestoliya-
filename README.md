# CA Tracker Bot — Setup Guide

Ye bot @stoolpresidente ke tweets check karta hai, pump.fun / Solana contract
address detect karta hai, DexScreener se verify karta hai, aur Telegram par
alert bhejta hai.

## ⚠️ Zaroori Baatein

1. **Bot token abhi is file mein plain text mein hai.** Chat mein tumne ye token
   share kiya hai — recommend hai ki BotFather ko `/revoke` bolke naya token le lo
   aur wahi naya token yahan daalo.
2. **Ye tool sirf alert bhejta hai.** Koi auto-buy nahi karta — buy tum khud
   manually karoge, jaisa tumne chaha tha.
3. **Reliability**: `snscrape` free scraping library hai (koi official Twitter
   API key nahi chahiye), lekin Twitter/X apna structure change karta rehta hai
   jisse kabhi-kabhi scraper break ho sakta hai. Agar ye rukta hai, library
   update karni padegi (`pip install --upgrade snscrape`) ya alternative
   scraper try karna padega.
4. **False positives**: Har detect hui CA scam/rug nahi hoti, aur har genuine
   CA bhi verify nahi hogi turant (naye tokens ko DexScreener par index hone
   mein kuch second lag sakte hain). Trust apni judgment par karo, ye tool
   sirf speed ke liye hai.

## Deploy Ke Baad Kaise Check Karein (Test Mode)

Deploy hone ke turant baad ye cheezein dekho:

1. **Startup message**: Telegram par turant "✅ CA Tracker started..." aana chahiye.
   Agar ye aa gaya, matlab bot + Telegram connection sahi hai.

2. **Test alert (poora pipeline check)**: Render dashboard mein apni Web
   Service ke **Environment** tab mein jaake ek naya environment variable add
   karo:
   - Key: `TEST_MODE`
   - Value: `1`

   Save karte hi Render service ko redeploy karega. Startup ke turant baad ek
   **real test alert** aayega tumhare Telegram par (sample pump.fun CA use
   karke) — jisse confirm ho jayega ki CA-detection, DexScreener verification,
   aur Telegram delivery, sab sahi kaam kar rahe hain.

   Test complete hone ke baad `TEST_MODE` variable ko **delete** kar do,
   warna har restart par test alert aata rahega.

3. **Logs check**: Render ke "Logs" tab mein `Starting CA tracker...` dikhna
   chahiye, aur har 30 second mein koi error na aana — matlab background
   monitoring bhi chal rahi hai.

## Files
- `ca_tracker.py` — main script
- `requirements.txt` — dependencies

## Local Test (optional, apne PC/laptop par)
```bash
pip install -r requirements.txt
python ca_tracker.py
```

## Free-Forever Hosting — Render.com Web Service + UptimeRobot

Render ka "Background Worker" ab paid hai ($7/month se), isliye hum "Web
Service" (jo free hai) use karenge. Script ab ek chhota web server bhi
chalati hai (`/ping` route) — isse Render use "active web service" samajhta
hai. UptimeRobot har 10 minute mein isko ping karega taaki wo kabhi so na jaye.

**Step 1 — Render par deploy karo**
1. https://render.com par free account banao (GitHub se sign in kar sakte ho, card nahi chahiye)
2. Apna code GitHub repo mein daalo (naya repo banao, `ca_tracker.py` aur `requirements.txt` upload karo)
3. Render dashboard mein **New → Web Service** select karo (Background Worker NAHI)
4. Apna GitHub repo connect karo
5. Settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python ca_tracker.py`
   - Instance type: **Free**
6. **Create Web Service** click karo
7. Deploy hote hi Render tumhe ek URL dega (jaisa `https://ca-tracker.onrender.com`) — ise copy kar lo

**Step 2 — UptimeRobot se zinda rakho**
1. https://uptimerobot.com par free account banao
2. **Add New Monitor** → Type: "HTTP(s)"
3. URL mein daalo: `https://ca-tracker.onrender.com/ping` (apna wala URL daalna)
4. Monitoring interval: **5 minutes** (free plan ka minimum)
5. Save karo

Bas — ab Render tumhari script ko kabhi sulayega nahi (kyunki UptimeRobot har 5
min mein request bhejta rahega), aur ye poora setup **$0/month** hai, chahe CA
2 saal tak na aaye.

## Alternative (chhoti si limitation ke saath) — Railway.app

Agar Render se dikkat aaye, Railway try kar sakte ho — 30-day trial mein $5
free credit milta hai, uske baad **$1/month** (bahut kam) charge hota hai.
Zero-cost nahi hai lekin bahut sasta aur zyada reliable hai.
1. https://railway.app par sign up karo
2. **New Project → Deploy from GitHub repo**
3. Apna repo select karo — Railway khud detect kar lega Python project hai
4. Deploy hone do

## Bot Ko Update Karna

Agar future mein aur accounts track karne ho, `TWITTER_USERNAME` variable ko
list mein convert karna padega — tab bata dena, main update kar dunga.
