from js import Response, fetch, Object
from pyodide.ffi import to_js
import json

async def on_fetch(request, env):
    try:
        TOKEN = str(env.TELEGRAM_BOT_TOKEN).strip()
        GROQ_KEY = str(env.GROQ_API_KEY).strip()

        if request.method == "POST":
            raw = await request.text()
            body = json.loads(raw)

            if "message" in body and "text" in body["message"]:
                chat_id = body["message"]["chat"]["id"]
                user_text = body["message"]["text"]

                groq_payload = json.dumps({
                    "model": "moonshotai/kimi-k2-instruct",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Sen Fedra adında zeki bir yapay zeka asistanısın. "
                                "Kullanıcıya yardımcı ol. "
                                "Sadece soran olursa: Seni Ziya Yılmaz geliştirdi, adın Fedra. "
                                "Sorulmadıkça kendini tanıtma veya kim olduğunu açıklama. "
                                "Her zaman yalnızca düzgün Türkçe kullan, başka dil karakteri karıştırma."
                            )
                        },
                        {"role": "user", "content": user_text}
                    ]
                })

                groq_res = await fetch(
                    "https://api.groq.com/openai/v1/chat/completions",
                    to_js({
                        "method": "POST",
                        "body": groq_payload,
                        "headers": {
                            "Authorization": f"Bearer {GROQ_KEY}",
                            "Content-Type": "application/json"
                        }
                    }, dict_converter=Object.fromEntries)
                )

                groq_raw = await groq_res.text()
                groq_data = json.loads(groq_raw)

                if "choices" in groq_data:
                    answer = groq_data["choices"][0]["message"]["content"]
                else:
                    answer = f"⚠️ Hata: {json.dumps(groq_data.get('error', 'Bilinmeyen hata'))}"

                tg_payload = json.dumps({"chat_id": chat_id, "text": answer})
                await fetch(
                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    to_js({
                        "method": "POST",
                        "body": tg_payload,
                        "headers": {"Content-Type": "application/json"}
                    }, dict_converter=Object.fromEntries)
                )

            return Response.new("OK", status=200)

        return Response.new("✅ Fedra Aktif!", status=200)

    except Exception as e:
        err = f"HATA {type(e).__name__}: {str(e)}"
        return Response.new(err, status=500)
