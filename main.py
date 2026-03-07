from js import Response, fetch, Object
from pyodide.ffi import to_js
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

                # --- Groq API Çağrısı ---
                groq_url = "https://api.groq.com/openai/v1/chat/completions"
                groq_payload = {
                    "model": "llama3-70b-8192",
                    "messages": [
                        {"role": "system", "content": "Sen Fedra isimli zeki bir asistansın."},
                        {"role": "user", "content": user_text}
                    ]
                }

                # ✅ DÜZELTME: fetch'e JS objesi olarak options geçiriliyor
                groq_res = await fetch(
                    groq_url,
                    to_js({
                        "method": "POST",
                        "body": json.dumps(groq_payload),
                        "headers": {
                            "Authorization": f"Bearer {GROQ_KEY}",
                            "Content-Type": "application/json"
                        }
                    }, dict_converter=Object.fromEntries)
                )

                groq_data = await groq_res.json()
                # pyodide JS objesi → Python dict'e çevir
                groq_dict = groq_data.to_py()

                if "choices" in groq_dict:
                    answer = groq_dict["choices"][0]["message"]["content"]
                else:
                    error_info = groq_dict.get("error", "Bilinmeyen hata")
                    answer = f"⚠️ Groq Hatası: {json.dumps(error_info)}"

                # --- Telegram'a Cevap Gönder ---
                tg_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
                await fetch(
                    tg_url,
                    to_js({
                        "method": "POST",
                        "body": json.dumps({"chat_id": chat_id, "text": answer}),
                        "headers": {"Content-Type": "application/json"}
                    }, dict_converter=Object.fromEntries)
                )

            return Response.new("OK", status=200)

        return Response.new("✅ Fedra Groq 70B Sistemi Aktif ve Mesaj Bekliyor!", status=200)

    except Exception as e:
        return Response.new(f"❌ Kritik Sistem Hatası: {str(e)}", status=200)
