from js import Response, fetch
import json

async def on_fetch(request, env):
    try:
        TOKEN = str(env.TELEGRAM_BOT_TOKEN).strip()
        GROQ_KEY = str(env.GROQ_API_KEY).strip()
        
        if request.method == "POST":
            body = await request.json()
            
            if "message" in body and "text" in body["message"]:
                chat_id = body["message"]["chat"]["id"]
                user_text = body["message"]["text"]
                
                # 1. Groq API Çağrısı (Llama 3 kullanıyoruz)
                groq_url = "https://api.groq.com/openai/v1/chat/completions"
                groq_payload = {
                    "model": "llama3-8b-8192",
                    "messages": [{"role": "user", "content": user_text}]
                }
                
                groq_res = await fetch(groq_url, 
                    method="POST", 
                    body=json.dumps(groq_payload), 
                    headers={
                        "Authorization": f"Bearer {GROQ_KEY}",
                        "Content-Type": "application/json"
                    }
                )
                
                groq_data = await groq_res.json()
                
                # Groq cevabını ayıkla
                if "choices" in groq_data:
                    reply = groq_data["choices"][0]["message"]["content"]
                else:
                    reply = f"Groq Hatası: {json.dumps(groq_data)}"
                
                # 2. Telegram'a Gönder
                tg_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
                await fetch(tg_url, method="POST", body=json.dumps({"chat_id": chat_id, "text": reply}), headers={"Content-Type": "application/json"})
                
            return Response.new("OK", status=200)
            
        return Response.new("Fedra Groq Sistemi Aktif!", status=200)
    except Exception as e:
        return Response.new(f"Hata: {str(e)}", status=200)
