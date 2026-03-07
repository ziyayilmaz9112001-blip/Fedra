from js import Response, fetch
import json

async def on_fetch(request, env):
    TOKEN = env.TELEGRAM_BOT_TOKEN
    GEMINI_KEY = env.GEMINI_API_KEY
    
    if request.method == "POST":
        try:
            body = await request.json()
            if "message" in body and "text" in body["message"]:
                chat_id = body["message"]["chat"]["id"]
                user_text = body["message"]["text"]
                
                gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
                gemini_payload = {
                    "contents": [{"parts": [{"text": f"Senin adın Fedra. Ziya'nın asistanısın. Soru: {user_text}"}]}]
                }
                
                gemini_res = await fetch(gemini_url, method="POST", body=json.dumps(gemini_payload), headers={"Content-Type": "application/json"})
                gemini_data = await gemini_res.json()
                
                reply = gemini_data["candidates"][0]["content"]["parts"][0]["text"]
                send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
                await fetch(send_url, method="POST", body=json.dumps({"chat_id": chat_id, "text": reply}), headers={"Content-Type": "application/json"})
                
            return Response.new("OK", status=200)
        except Exception as e:
            return Response.new(str(e), status=500)
            
    return Response.new("Fedra Python ile GitHub üzerinden yayında!", status=200)
# test
# aktif
