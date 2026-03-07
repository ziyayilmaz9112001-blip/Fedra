from js import Response, fetch
import json

async def on_fetch(request, env):
    try:
        # 1. Değişkenleri güvenli bir şekilde çekelim
        TOKEN = str(env.TELEGRAM_BOT_TOKEN).strip()
        GEMINI_KEY = str(env.GEMINI_API_KEY).strip()
        
        # Sadece Telegram'dan gelen POST isteklerini işle
        if request.method == "POST":
            body = await request.json()
            
            # Telegram mesaj içeriğini kontrol et
            if "message" in body and "text" in body["message"]:
                chat_id = body["message"]["chat"]["id"]
                user_text = body["message"]["text"]
                
                # 2. Gemini API Çağrısı
                gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
                gemini_payload = {
                    "contents": [{"parts": [{"text": user_text}]}]
                }
                
                gemini_res = await fetch(gemini_url, method="POST", body=json.dumps(gemini_payload), headers={"Content-Type": "application/json"})
                gemini_data = await gemini_res.json()
                
                # Gemini'den gelen cevabı ayıkla
                if "candidates" in gemini_data:
                    reply = gemini_data["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    reply = "Gemini hata verdi: " + json.dumps(gemini_data)
                
                # 3. Telegram'a Cevap Gönder
                send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
                await fetch(send_url, method="POST", body=json.dumps({"chat_id": chat_id, "text": reply}), headers={"Content-Type": "application/json"})
                
            return Response.new("OK", status=200)
            
        return Response.new("Fedra Python Sistemi Aktif!", status=200)
        
    except Exception as e:
        # Hatayı direkt sayfaya yazdır ki ne olduğunu görelim
        return Response.new(f"Hata oluştu: {str(e)}", status=500)
