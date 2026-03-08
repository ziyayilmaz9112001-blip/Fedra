from js import Response, fetch, Object
from pyodide.ffi import to_js
import json

async def tavily_search(query, tavily_key):
    """Tavily ile web araması yap, sonuçları özetle döndür."""
    payload = json.dumps({
        "api_key": tavily_key,
        "query": query,
        "search_depth": "basic",
        "max_results": 3
    })
    res = await fetch(
        "https://api.tavily.com/search",
        to_js({
            "method": "POST",
            "body": payload,
            "headers": {"Content-Type": "application/json"}
        }, dict_converter=Object.fromEntries)
    )
    raw = await res.text()
    data = json.loads(raw)

    if "results" not in data:
        return None

    # İlk 3 sonucun başlık + içeriğini birleştir
    snippets = []
    for r in data["results"][:3]:
        title = r.get("title", "")
        content = r.get("content", "")[:300]
        url = r.get("url", "")
        snippets.append(f"- {title}: {content} ({url})")

    return "\n".join(snippets)


async def on_fetch(request, env):
    try:
        TOKEN = str(env.TELEGRAM_BOT_TOKEN).strip()
        GROQ_KEY = str(env.GROQ_API_KEY).strip()
        TAVILY_KEY = str(env.TAVILY_API_KEY).strip()

        if request.method == "POST":
            raw = await request.text()
            body = json.loads(raw)

            if "message" in body and "text" in body["message"]:
                chat_id = body["message"]["chat"]["id"]
                user_text = body["message"]["text"]

                # Tavily ile güncel web araması yap
                search_results = await tavily_search(user_text, TAVILY_KEY)

                # Sistem promptuna arama sonuçlarını ekle
                if search_results:
                    system_content = (
                        "Sen Fedra adında zeki bir yapay zeka asistanısın. "
                        "Sadece soran olursa: Seni Ziya Yılmaz geliştirdi, adın Fedra. "
                        "Sorulmadıkça kendini tanıtma. "
                        "Her zaman yalnızca düzgün Türkçe kullan, başka dil karakteri karıştırma.\n\n"
                        "Aşağıda kullanıcının sorusuna ilişkin güncel web arama sonuçları var. "
                        "Bu bilgilere dayanarak cevap ver:\n\n"
                        f"{search_results}"
                    )
                else:
                    system_content = (
                        "Sen Fedra adında zeki bir yapay zeka asistanısın. "
                        "Sadece soran olursa: Seni Ziya Yılmaz geliştirdi, adın Fedra. "
                        "Sorulmadıkça kendini tanıtma. "
                        "Her zaman yalnızca düzgün Türkçe kullan, başka dil karakteri karıştırma."
                    )

                groq_payload = json.dumps({
                    "model": "moonshotai/kimi-k2-instruct",
                    "messages": [
                        {"role": "system", "content": system_content},
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
