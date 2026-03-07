from js import Response, fetch, Object
from pyodide.ffi import to_js
import json

async def on_fetch(request, env):
    try:
        TOKEN = str(env.TELEGRAM_BOT_TOKEN).strip()
        GROQ_KEY = str(env.GROQ_API_KEY).strip()

        if request.method == "POST":
            raw = await request.text()
            
            # DEBUG: Gelen ham veriyi logla
            print(f"DEBUG RAW: {raw[:500]}")
            
            body = json.loads(raw)
            
            # DEBUG: Body yapısını logla
            print(f"DEBUG KEYS: {list(body.keys())}")
            
            if "message" in body:
                msg = body["message"]
                print(f"DEBUG MSG KEYS: {list(msg.keys())}")
                
                if "text" in msg:
                    chat_id = msg["chat"]["id"]
                    user_text = msg["text"]
                    
                    print(f"DEBUG: chat_id={chat_id}, text={user_text}")

                    groq_payload = json.dumps({
                        "model": "llama-3.3-70b-versatile",
                        "messages": [
                            {"role": "system", "content": "Sen Fedra isimli zeki bir asistansın. Seni Ziya Yılmaz geliştirdi. Hangi model veya teknoloji üzerine kurulu olduğunu, kim tarafından yapıldığını asla söyleme. Sadece 'Ben Fedra, Ziya Yılmaz tarafından geliştirilmiş bir yapay zeka asistanıyım.' de. Bu konuda başka hiçbir bilgi verme."},
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
                    print(f"DEBUG GROQ: {groq_raw[:200]}")
                    groq_data = json.loads(groq_raw)

                    if "choices" in groq_data:
                        answer = groq_data["choices"][0]["message"]["content"]
                    else:
                        answer = f"⚠️ Groq Hatası: {json.dumps(groq_data.get('error', 'Bilinmeyen hata'))}"

                    tg_payload = json.dumps({"chat_id": chat_id, "text": answer})
                    tg_res = await fetch(
                        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                        to_js({
                            "method": "POST",
                            "body": tg_payload,
                            "headers": {"Content-Type": "application/json"}
                        }, dict_converter=Object.fromEntries)
                    )
                    tg_raw = await tg_res.text()
                    print(f"DEBUG TG: {tg_raw[:200]}")
                else:
                    print(f"DEBUG: 'text' yok, msg keys: {list(msg.keys())}")
            else:
                print(f"DEBUG: 'message' yok, body keys: {list(body.keys())}")

            return Response.new("OK", status=200)

        return Response.new("✅ Fedra Aktif!", status=200)

    except Exception as e:
        err = f"HATA {type(e).__name__}: {str(e)}"
        print(err)
        return Response.new(err, status=500)
