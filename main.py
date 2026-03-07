from js import Response, fetch
import json

async def on_fetch(request, env):
    try:
        # 1. Değişkenleri Çek (Varsayılan boş string atayarak korumaya al)
        TOKEN = getattr(env, "TELEGRAM_BOT_TOKEN", "").strip()
        GEMINI_KEY = getattr(env, "GEMINI_API_KEY", "").strip()
        
        if request.method == "POST":
            data = await request.json()
            
            if "message" in data and "text" in data["message"]:
                chat_id = data["message"]["chat"]["id"]
                user_msg = data["message"]["text"]
                
                # 2. Gemini API İsteği
                gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
                
                payload = {
                    "contents": [{
                        "parts": [{"text": user_msg}]
                    }]
                }
                
                res = await fetch(gemini_url, 
                    method="POST", 
                    body=json.dumps(payload), 
                    headers={"Content-Type": "application/json"}
                )
                
                res_data = await res.json()
                
                # Gemini cevabını kontrol et
                if "candidates" in res_data:
                    reply_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    reply_text = f"Sistem hatası (Gemini): {json.dumps(res_data)}"

                # 3. Telegram'a Gönder
                tg_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
                await fetch(tg_url, 
                    method="POST", 
                    body=json.dumps({"chat_id": chat_id, "text": reply_text}),
                    headers={"Content-Type": "application/json"}
                )
            
            return Response.new("OK", status=200)
            
        return Response.new("Fedra Sistemi Aktif!", status=200)

    except Exception as e:
        # Burası çok kritik: 500 hatası aldığında sebebi sayfaya yazar
        return Response.new(f"Kritik Hata: {str(e)}", status=200) # 500 yerine 200 verip hatayı görelim
