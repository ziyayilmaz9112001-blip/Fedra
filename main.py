from js import Response, fetch, Object
from pyodide.ffi import to_js
from datetime import datetime, timezone, timedelta
import json

# Türkiye saati (UTC+3)
def get_turkey_time():
    tz = timezone(timedelta(hours=3))
    now = datetime.now(tz)
    days = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"]
    months = ["","Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
              "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]
    return f"{days[now.weekday()]} {now.day} {months[now.month]} {now.year}, saat {now.strftime('%H:%M')}"

async def needs_search(user_text, groq_key):
    """Kimi K2'ye sor: bu mesaj için web araması gerekli mi?"""
    payload = json.dumps({
        "model": "moonshotai/kimi-k2-instruct",
        "max_tokens": 10,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Kullanıcının mesajını analiz et. "
                    "Eğer güncel bilgi, haber, hava durumu, fiyat, spor sonucu gibi "
                    "gerçek zamanlı internete ihtiyaç duyulan bir soru ise sadece 'EVET' yaz. "
                    "Selamlama, sohbet, genel bilgi, matematik, fikir soruları için sadece 'HAYIR' yaz. "
                    "Başka hiçbir şey yazma."
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
    raw = await res.text()
    data = json.loads(raw)
    answer = data["choices"][0]["message"]["content"].strip().upper()
    return "EVET" in answer

async def tavily_search(query, tavily_key):
    payload = json.dumps({
        "api_key": tavily_key,
        "query": query,
        "search_depth": "advanced",
        "max_results": 3,
        "include_answer": True  # Tavily'nin kendi özetini de al
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

    snippets = []
    # Tavily'nin hazır özeti varsa önce onu ekle
    if data.get("answer"):
        snippets.append(f"Özet: {data['answer']}")

    for r in data["results"][:3]:
        title = r.get("title", "")
        content = r.get("content", "")[:400]
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

                # Şu anki Türkiye saati — her zaman doğru
                current_time = get_turkey_time()

                # Arama gerekli mi?
                search_needed = await needs_search(user_text, GROQ_KEY)
                search_results = None
                if search_needed:
                    search_results = await tavily_search(user_text, TAVILY_KEY)

                # Sistem promptu
                base_prompt = (
                    "Sen Fedra adında zeki bir yapay zeka asistanısın. "
                    "Sadece soran olursa: Seni Ziya Yılmaz geliştirdi, adın Fedra. "
                    "Sorulmadıkça kendini tanıtma. "
                    "Her zaman yalnızca düzgün Türkçe kullan, başka dil karakteri karıştırma.\n"
                    f"Şu anki tarih ve saat (Türkiye): {current_time}\n"
                )

                if search_results:
                    system_content = (
                        base_prompt +
                        "Aşağıdaki güncel web arama sonuçlarına dayanarak cevap ver:\n\n" +
                        search_results
                    )
                else:
                    system_content = base_prompt

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
