from js import Response, fetch, Object, Date
from pyodide.ffi import to_js
import json

def get_turkey_time():
    ms = Date.now()
    total_seconds = int(ms // 1000) + 3 * 3600
    days_since_epoch = total_seconds // 86400
    secs_today = total_seconds % 86400
    hour = secs_today // 3600
    minute = (secs_today % 3600) // 60
    y, remaining = 1970, days_since_epoch
    while True:
        leap = (y % 4 == 0 and y % 100 != 0) or y % 400 == 0
        days_in_year = 366 if leap else 365
        if remaining < days_in_year:
            break
        remaining -= days_in_year
        y += 1
    leap = (y % 4 == 0 and y % 100 != 0) or y % 400 == 0
    month_days = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    m, d = 1, 1
    for i, md in enumerate(month_days):
        if remaining < md:
            m = i + 1
            d = remaining + 1
            break
        remaining -= md
    day_names = ["Perşembe","Cuma","Cumartesi","Pazar","Pazartesi","Salı","Çarşamba"]
    month_names = ["","Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
                   "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]
    return f"{day_names[days_since_epoch % 7]} {d} {month_names[m]} {y}, saat {hour:02d}:{minute:02d}"


def is_weather_query(text):
    """Hava durumu sorusu mu?"""
    keywords = ["hava","derece","sıcaklık","yağmur","kar","fırtına","nem","rüzgar","hissedilen"]
    text_lower = text.lower()
    return any(k in text_lower for k in keywords)


async def needs_search(user_text, groq_key):
    """Arama gerekli mi?"""
    payload = json.dumps({
        "model": "moonshotai/kimi-k2-instruct",
        "max_tokens": 10,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Kullanıcının mesajını analiz et. "
                    "Güncel haber, hava durumu, fiyat, spor sonucu, borsa, döviz, "
                    "güncel olay gibi gerçek zamanlı internet gerektiren sorular için 'EVET' yaz. "
                    "Selamlama, sohbet, genel bilgi, tarih, matematik, fikir, tanım soruları için 'HAYIR' yaz. "
                    "Sadece EVET veya HAYIR yaz, başka hiçbir şey yazma."
                )
            },
            {"role": "user", "content": user_text}
        ]
    })
    res = await fetch(
        "https://api.groq.com/openai/v1/chat/completions",
        to_js({
            "method": "POST",
            "body": payload,
            "headers": {
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json"
            }
        }, dict_converter=Object.fromEntries)
    )
    data = json.loads(await res.text())
    answer = data["choices"][0]["message"]["content"].strip().upper()
    return "EVET" in answer


async def serper_search(query, serper_key):
    """Serper ile Google araması (genel sorgular)."""
    payload = json.dumps({"q": query, "num": 3, "hl": "tr"})
    res = await fetch(
        "https://google.serper.dev/search",
        to_js({
            "method": "POST",
            "body": payload,
            "headers": {
                "X-API-KEY": serper_key,
                "Content-Type": "application/json"
            }
        }, dict_converter=Object.fromEntries)
    )
    data = json.loads(await res.text())
    snippets = []

    # Answer box varsa önce onu al
    if data.get("answerBox"):
        ab = data["answerBox"]
        snippets.append(f"Özet: {ab.get('answer') or ab.get('snippet','')}")

    # Organik sonuçlar
    for r in data.get("organic", [])[:3]:
        snippets.append(f"- {r.get('title','')}: {r.get('snippet','')} ({r.get('link','')})")

    return "\n".join(snippets) if snippets else None


async def tavily_search(query, tavily_key):
    """Tavily ile hava durumu araması."""
    payload = json.dumps({
        "api_key": tavily_key,
        "query": query,
        "search_depth": "basic",
        "max_results": 3,
        "include_answer": True
    })
    res = await fetch(
        "https://api.tavily.com/search",
        to_js({
            "method": "POST",
            "body": payload,
            "headers": {"Content-Type": "application/json"}
        }, dict_converter=Object.fromEntries)
    )
    data = json.loads(await res.text())
    if "results" not in data:
        return None
    snippets = []
    if data.get("answer"):
        snippets.append(f"Özet: {data['answer']}")
    for r in data["results"][:3]:
        snippets.append(f"- {r.get('title','')}: {r.get('content','')[:400]} ({r.get('url','')})")
    return "\n".join(snippets)


async def on_fetch(request, env):
    try:
        TOKEN = str(env.TELEGRAM_BOT_TOKEN).strip()
        GROQ_KEY = str(env.GROQ_API_KEY).strip()
        TAVILY_KEY = str(env.TAVILY_API_KEY).strip()
        SERPER_KEY = str(env.SERPER_API_KEY).strip()

        if request.method == "POST":
            body = json.loads(await request.text())

            if "message" in body and "text" in body["message"]:
                chat_id = body["message"]["chat"]["id"]
                user_text = body["message"]["text"]

                current_time = get_turkey_time()
                search_results = None

                search_needed = await needs_search(user_text, GROQ_KEY)

                if search_needed:
                    if is_weather_query(user_text):
                        # Hava durumu → Tavily (daha doğru)
                        search_results = await tavily_search(user_text, TAVILY_KEY)
                    else:
                        # Genel arama → Serper (2500 ücretsiz)
                        search_results = await serper_search(user_text, SERPER_KEY)

                base_prompt = (
                    "Sen Fedra adında zeki bir yapay zeka asistanısın. "
                    "Sadece soran olursa: Seni Ziya Yılmaz geliştirdi, adın Fedra. "
                    "Sorulmadıkça kendini tanıtma. "
                    "Her zaman yalnızca düzgün Türkçe kullan, başka dil karakteri karıştırma.\n"
                    f"Şu anki tarih ve saat (Türkiye): {current_time}\n"
                )

                system_content = (
                    base_prompt +
                    "Aşağıdaki güncel web arama sonuçlarına dayanarak cevap ver:\n\n" + search_results
                    if search_results else base_prompt
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

                groq_data = json.loads(await groq_res.text())

                if "choices" in groq_data:
                    answer = groq_data["choices"][0]["message"]["content"]
                else:
                    answer = f"⚠️ Hata: {json.dumps(groq_data.get('error', 'Bilinmeyen hata'))}"

                await fetch(
                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    to_js({
                        "method": "POST",
                        "body": json.dumps({"chat_id": chat_id, "text": answer}),
                        "headers": {"Content-Type": "application/json"}
                    }, dict_converter=Object.fromEntries)
                )

            return Response.new("OK", status=200)

        return Response.new("✅ Fedra Aktif!", status=200)

    except Exception as e:
        return Response.new(f"HATA {type(e).__name__}: {str(e)}", status=500)
