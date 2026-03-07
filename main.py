from js import Response, fetch
import json

async def on_fetch(request, env):
    try:
        # 1. Ortam Değişkenlerini Tanımla
        TOKEN = str(env.TELEGRAM_BOT_TOKEN).strip()
        GROQ_KEY = str(env.GROQ_API_KEY).strip()
        
        # 2. Telegram'dan Gelen POST İsteğini Yakala
        if request.method == "POST":
            body = await request.json()
            
            if "message" in body and "text" in body["message"]:
                chat_id = body["message"]["chat"]["id"]
                user_text = body["message"]["text"]
                
                # 3. Groq API (Llama 3 70B) Çağrısı
                groq_url = "https://api.groq.com/openai/v1/chat/completions"
                groq_payload = {
                    "model": "llama3-70b-8192", # Burayı 70B yaptık
                    "messages": [
                        {"role": "system", "content": "Sen Fedra isimli, zeki ve yardımsever bir asistansın."},
                        {"role": "user", "content": user_text}
                    ],
                    "temperature": 0.7
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
                
                # 4. Yanıtı Ayıkla ve Telegram'a Gönder
                if "choices" in groq_data:
                    answer = groq_data["choices"][0]["message"]["content"]
                else:
                    answer = f"⚠️ Groq Hatası: {json.dumps(groq_data)}"
                
                # Telegram sendMessage API
                await fetch(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                    method="POST", 
                    body=json.dumps({"chat_id": chat_id, "text": answer}),
                    headers={"Content-Type": "application/json"}
                )
            
            return Response.new("OK", status=200)
            
        # Tarayıcıdan girildiğinde görünen mesaj
        return Response.new("Fedra Groq 70B Sistemi Aktif!", status=200)

    except Exception as e:
        # Kritik bir hata olursa tarayıcı loguna basar
        return Response.new(f"Sistem Hatası: {str(e)}", status=200)
