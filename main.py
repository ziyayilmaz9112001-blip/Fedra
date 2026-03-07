from js import Response, fetch
import json

async def on_fetch(request, env):
    try:
        # 1. Değişkenleri Cloudflare'den güvenli şekilde çek
        TOKEN = str(env.TELEGRAM_BOT_TOKEN).strip()
        GROQ_KEY = str(env.GROQ_API_KEY).strip()
        
        # Sadece POST isteklerini (Telegram'dan gelen mesajları) işle
        if request.method == "POST":
            body = await request.json()
            
            # Gelen verinin içinde mesaj ve metin var mı kontrol et
            if "message" in body and "text" in body["message"]:
                chat_id = body["message"]["chat"]["id"]
                user_text = body["message"]["text"]
                
                # 2. Groq API (Llama 3 70B) Çağrısı
                groq_url = "https://api.groq.com/openai/v1/chat/completions"
                groq_payload = {
                    "model": "llama3-70b-8192",
                    "messages": [
                        {"role": "system", "content": "Sen Fedra isimli zeki bir asistansın."},
                        {"role": "user", "content": user_text}
                    ]
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
                
                # Groq'tan gelen cevabı ayıkla
                if "choices" in groq_data:
                    answer = groq_data["choices"][0]["message"]["content"]
                else:
                    # Eğer Groq hata dönerse hatayı Telegram'a gönder
                    answer = f"⚠️ Groq Hatası: {json.dumps(groq_data.get('error', 'Bilinmeyen hata'))}"
                
                # 3. Telegram'a Cevabı Geri Gönder
                tg_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
                await fetch(tg_url, 
                    method="POST", 
                    body=json.dumps({"chat_id": chat_id, "text": answer}),
                    headers={"Content-Type": "application/json"}
                )
            
            return Response.new("OK", status=200)
            
        # Tarayıcıdan girildiğinde sistemin durumunu göster
        return Response.new("✅ Fedra Groq 70B Sistemi Aktif ve Mesaj Bekliyor!", status=200)

    except Exception as e:
        # Kodun içinde bir patlama olursa tarayıcıda hatayı göster
        return Response.new(f"❌ Kritik Sistem Hatası: {str(e)}", status=200)
