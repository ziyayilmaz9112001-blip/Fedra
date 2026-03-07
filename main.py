from js import Response, fetch
import json

async def on_fetch(request, env):
    try:
        TOKEN = str(env.TELEGRAM_BOT_TOKEN).strip()
        GEMINI_KEY = str(env.GEMINI_API_KEY).strip()
        
        if request.method == "POST":
            body = await request.json()
            
            if "message" in body and "text" in body["message"]:
                chat_id = body["message"]["chat"]["id"]
                user_text = body["message"]["text"]
                
                # 1. Gemini'ye Sinyal Gönder
                gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
                gemini_payload = {"contents": [{"parts": [{"text": user_text}]}]}
                
                gemini_res = await fetch(gemini_url, method="POST", body=json.dumps(gemini_payload), headers={"Content-Type": "application/json"})
                gemini_data = await gemini_res.json()
                
                # Gemini cevabını kontrol et
                if "candidates" in gemini_data:
                    reply = gemini_data["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    # Hata varsa hatayı Telegram'a gönder ki görelim
                    reply = f"Gemini Hatası: {json.dumps(gemini_data)}"
                
                # 2. Telegram'a Cevap Gönder
                tg_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
                await fetch(tg_url, method="POST", body=json.dumps({"chat_id": chat_id, "text": reply}), headers={"Content-Type": "application/json"})
                
            return Response.new("OK", status=200)
            
        return Response.new("Fedra Aktif!", status=200)
    except Exception as e:
        # Eğer bir hata olursa ekrana yazdır
        return Response.new(f"Kod Hatası: {str(e)}", status=200)
