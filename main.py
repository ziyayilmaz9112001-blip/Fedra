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
    keywords = ["hava","derece","sıcaklık","yağmur","kar","fırtına","nem","rüzgar","hissedilen"]
    return any(k in text.lower() for k in keywords)


def detect_crypto(text):
    t = text.lower()
    coins = {
        "bitcoin": "bitcoin", "btc": "bitcoin",
        "ethereum": "ethereum", "eth": "ethereum",
        "solana": "solana", "sol": "solana",
        "ripple": "ripple", "xrp": "ripple",
        "dogecoin": "dogecoin", "doge": "dogecoin",
        "bnb": "binancecoin", "binance": "binancecoin",
        "cardano": "cardano", "ada": "cardano",
        "avalanche": "avalanche-2", "avax": "avalanche-2",
        "polkadot": "polkadot", "dot": "polkadot",
        "litecoin": "litecoin", "ltc": "litecoin",
    }
    for keyword, coin_id in coins.items():
        if keyword in t:
            return coin_id
    return None


async def get_voice_file_url(file_id, token):
    """Telegram'dan ses dosyasının URL'ini al."""
    res = await fetch(
        f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}",
        to_js({"method": "GET"}, dict_converter=Object.fromEntries)
    )
    data = json.loads(await res.text())
    if not data.get("ok"):
        return None
    file_path = data["result"]["file_path"]
    return f"https://api.telegram.org/file/bot{token}/{file_path}"


async def transcribe_voice(file_url, groq_key):
    """Groq Whisper ile sesi metne çevir — manuel multipart."""
    # Ses dosyasını indir
    audio_res = await fetch(
        file_url,
        to_js({"method": "GET"}, dict_converter=Object.fromEntries)
    )
    audio_bytes = await audio_res.arrayBuffer()

    # Python'da Uint8Array'den bytes'a çevir
    from js import Uint8Array
    audio_uint8 = Uint8Array.new(audio_bytes)
    audio_data = bytes(audio_uint8.to_py())

    # Manuel multipart/form-data oluştur
    boundary = "----GroqBoundary7MA4YWxkTrZu0gW"
    body_parts = []
    body_parts.append(f"--{boundary}
".encode())
    body_parts.append(b'Content-Disposition: form-data; name="file"; filename="voice.ogg"
')
    body_parts.append(b'Content-Type: audio/ogg

')
    body_parts.append(audio_data)
    body_parts.append(f"
--{boundary}
".encode())
    body_parts.append(b'Content-Disposition: form-data; name="model"

')
    body_parts.append(b'whisper-large-v3-turbo')
    body_parts.append(f"
--{boundary}
".encode())
    body_parts.append(b'Content-Disposition: form-data; name="language"

')
    body_parts.append(b'tr')
    body_parts.append(f"
--{boundary}
".encode())
    body_parts.append(b'Content-Disposition: form-data; name="response_format"

')
    body_parts.append(b'json')
    body_parts.append(f"
--{boundary}--
".encode())
    body = b"".join(body_parts)

    # Uint8Array olarak gönder
    from js import Uint8Array as JSUint8Array
    js_body = JSUint8Array.new(len(body))
    for i, byte in enumerate(body):
        js_body[i] = byte

    res = await fetch(
        "https://api.groq.com/openai/v1/audio/transcriptions",
        to_js({
            "method": "POST",
            "body": js_body,
            "headers": {
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "multipart/form-data; boundary=" + boundary
            }
        }, dict_converter=Object.fromEntries)
    )
    raw = await res.text()
    data = json.loads(raw)
    return data.get("text", "").strip()


async def binance_price(coin_id):
    symbol_map = {
        "bitcoin": ("BTCUSDT", "Bitcoin"),
        "ethereum": ("ETHUSDT", "Ethereum"),
        "solana": ("SOLUSDT", "Solana"),
        "ripple": ("XRPUSDT", "XRP"),
        "dogecoin": ("DOGEUSDT", "Dogecoin"),
        "binancecoin": ("BNBUSDT", "BNB"),
        "cardano": ("ADAUSDT", "Cardano"),
        "avalanche-2": ("AVAXUSDT", "Avalanche"),
        "polkadot": ("DOTUSDT", "Polkadot"),
        "litecoin": ("LTCUSDT", "Litecoin"),
    }
    if coin_id not in symbol_map:
        return None
    symbol, name = symbol_map[coin_id]
    res_price = await fetch(
        f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}",
        to_js({"method": "GET"}, dict_converter=Object.fromEntries)
    )
    price_data = json.loads(await res_price.text())
    if "price" not in price_data:
        return None
    usd = float(price_data["price"])
    res_change = await fetch(
        f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}",
        to_js({"method": "GET"}, dict_converter=Object.fromEntries)
    )
    change_data = json.loads(await res_change.text())
    change = float(change_data.get("priceChangePercent", 0))
    change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
    return f"{name} anlık fiyatı: ${usd:,.2f} USD (24s değişim: {change_str})"


async def needs_search(user_text, groq_key):
    payload = json.dumps({
        "model": "moonshotai/kimi-k2-instruct",
        "max_tokens": 10,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Kullanıcının mesajını analiz et. "
                    "Şu sorular için KESİNLİKLE 'HAYIR' yaz: tarih, saat, gün, selamlama, "
                    "sohbet, genel bilgi, matematik, fikir, tanım, kim olduğun, kripto fiyatı. "
                    "Yalnızca şunlar için 'EVET' yaz: hava durumu, güncel haber, "
                    "spor sonucu, borsa, döviz kuru, altın fiyatı, seçim sonuçları. "
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


def serper_result_quality(data):
    score = 0
    if data.get("answerBox"):
        score += 2
    if data.get("sportsResults") and data["sportsResults"].get("gameSpotlight"):
        score += 2
    organics = data.get("organic", [])
    if organics:
        score += 1
    snippets = [r.get("snippet","") for r in organics[:3]]
    avg_len = sum(len(s) for s in snippets) / max(len(snippets), 1)
    if avg_len < 50:
        score -= 1
    return score


async def serper_search(query, serper_key):
    payload = json.dumps({"q": query, "num": 5, "hl": "tr"})
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
    quality = serper_result_quality(data)
    snippets = []
    if data.get("answerBox"):
        ab = data["answerBox"]
        answer = ab.get("answer") or ab.get("snippet") or ""
        if answer:
            snippets.append(f"Özet: {answer}")
    if data.get("sportsResults"):
        sr = data["sportsResults"]
        gs = sr.get("gameSpotlight", {})
        if gs:
            home = gs.get("homeTeam", {})
            away = gs.get("awayTeam", {})
            snippets.append(
                f"Maç: {home.get('name','')} {home.get('score','')} - "
                f"{away.get('score','')} {away.get('name','')} | {sr.get('title','')}"
            )
        else:
            snippets.append(f"Spor: {json.dumps(sr, ensure_ascii=False)[:400]}")
    for r in data.get("organic", [])[:4]:
        snippets.append(f"- {r.get('title','')}: {r.get('snippet','')}")
    result = "\n".join(snippets) if snippets else None
    return result, quality


async def tavily_search(query, tavily_key):
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
        snippets.append(f"- {r.get('title','')}: {r.get('content','')[:400]}")
    return "\n".join(snippets) if snippets else None


async def smart_search(query, serper_key, tavily_key, is_weather):
    if is_weather:
        return await tavily_search(query, tavily_key)
    result, quality = await serper_search(query, serper_key)
    if quality >= 2:
        return result
    tavily_result = await tavily_search(query, tavily_key)
    if tavily_result:
        return ((result or "") + "\n\n[Ek kaynak]\n" + tavily_result).strip()
    return result


async def get_ai_response(user_text, search_results, current_time, groq_key):
    base_prompt = (
        "Sen Fedra adında zeki bir yapay zeka asistanısın. "
        "Sadece soran olursa: Seni Ziya Yılmaz geliştirdi, adın Fedra. "
        "Sorulmadıkça kendini tanıtma. "
        "Her zaman yalnızca düzgün Türkçe kullan, başka dil karakteri karıştırma. "
        "ASLA link veya URL paylaşma. Bilgiyi doğrudan ve net söyle. "
        "Eğer arama sonuçları yetersiz veya çelişkiliyse bunu dürüstçe belirt; "
        "kesinlikle bilgi uydurma veya tahmin yürütme.\n"
        f"Şu anki tarih ve saat (Türkiye): {current_time}\n"
    )
    system_content = (
        base_prompt + "Aşağıdaki güncel veriye dayanarak cevap ver:\n\n" + search_results
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
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json"
            }
        }, dict_converter=Object.fromEntries)
    )
    groq_data = json.loads(await groq_res.text())
    if "choices" in groq_data:
        return groq_data["choices"][0]["message"]["content"]
    return f"⚠️ Hata: {json.dumps(groq_data.get('error', 'Bilinmeyen hata'))}"


async def send_message(chat_id, text, token):
    await fetch(
        f"https://api.telegram.org/bot{token}/sendMessage",
        to_js({
            "method": "POST",
            "body": json.dumps({"chat_id": chat_id, "text": text}),
            "headers": {"Content-Type": "application/json"}
        }, dict_converter=Object.fromEntries)
    )


async def on_fetch(request, env):
    try:
        TOKEN = str(env.TELEGRAM_BOT_TOKEN).strip()
        GROQ_KEY = str(env.GROQ_API_KEY).strip()
        TAVILY_KEY = str(env.TAVILY_API_KEY).strip()
        SERPER_KEY = str(env.SERPER_API_KEY).strip()

        if request.method == "POST":
            body = json.loads(await request.text())

            if "message" in body:
                msg = body["message"]
                chat_id = msg["chat"]["id"]
                current_time = get_turkey_time()
                user_text = None

                # Sesli mesaj kontrolü
                if "voice" in msg:
                    try:
                        file_id = msg["voice"]["file_id"]
                        file_url = await get_voice_file_url(file_id, TOKEN)
                        if file_url:
                            user_text = await transcribe_voice(file_url, GROQ_KEY)
                            if not user_text:
                                await send_message(chat_id, "❌ Ses anlaşılamadı, tekrar dener misin?", TOKEN)
                                return Response.new("OK", status=200)
                        else:
                            await send_message(chat_id, "❌ Ses dosyası alınamadı.", TOKEN)
                            return Response.new("OK", status=200)
                    except Exception as voice_err:
                        await send_message(chat_id, f"🔴 Ses hatası: {type(voice_err).__name__}: {str(voice_err)[:200]}", TOKEN)
                        return Response.new("OK", status=200)

                # Yazılı mesaj
                elif "text" in msg:
                    user_text = msg["text"]

                if not user_text:
                    return Response.new("OK", status=200)

                # Arama ve cevap
                search_results = None
                coin_id = detect_crypto(user_text)
                if coin_id:
                    search_results = await binance_price(coin_id)
                else:
                    search_needed = await needs_search(user_text, GROQ_KEY)
                    if search_needed:
                        weather = is_weather_query(user_text)
                        search_results = await smart_search(
                            user_text, SERPER_KEY, TAVILY_KEY, weather
                        )

                answer = await get_ai_response(user_text, search_results, current_time, GROQ_KEY)
                await send_message(chat_id, answer, TOKEN)

            return Response.new("OK", status=200)

        return Response.new("✅ Fedra Aktif!", status=200)

    except Exception as e:
        return Response.new(f"HATA {type(e).__name__}: {str(e)}", status=500)
