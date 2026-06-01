#!/usr/bin/env python3
"""
Fuji Classic 一人予約 robot (PART 2) — detail-page driven
----------------------------------------------------------
The list page mixes up dates on some special plans, so it is NOT trusted for
date/occupancy. Instead we use the list ONLY to enumerate the open plan ids,
then read each plan's DETAIL page ("ご予約状況"), which is the single source of
truth for:
  - play date (= confirmation date + 1 day)
  - tee time / IN-OUT
  - overseas-golfer price (lunch included)
  - real occupancy (named entrants vs "エントリー受付中" empty seats)
  - whether one of the entrants is us ("プリザーブゴルフ")

No login required (public logon=OFF endpoint).
Run:  python3 fetch_slots.py
"""
import re, json, os, time, datetime, urllib.request, urllib.error, sys

PID, RENT_CID = "V2LsLwGTUdG4IS", "190002801"
BASE   = "https://www.valuegolf.co.jp/one"
PORTAL = f"{BASE}/portal_top.cfm?pid={PID}&logon=OFF"
HERE   = os.path.dirname(os.path.abspath(__file__))
OURS   = "プリザーブゴルフ"
WEEK   = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": PORTAL})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", errors="ignore")

def list_oz():
    ts = int(time.time() * 1000)
    params = (f"d={ts}&pid={PID}&rent_cid={RENT_CID}&exh_flg=V&oMbId=&mbDispDays=3"
              f"&pageRows=3000&pageNo=0&openGroupFlg=1&ogmFlg=0&resultYourpriceFlg=0"
              f"&startUpType=0&prm2z=5&_={ts}")
    html = get(f"{BASE}/more_result2.cfm?{params}")
    seen, order = set(), []
    for oz in re.findall(r"plan\.cfm\?[^\"']*?oz=(T\d+)", html):
        if oz not in seen:
            seen.add(oz); order.append(oz)
    return order

def parse_detail(html):
    # confirmation date -> play date (= +1 day). Loose match (weekday/time vary).
    m = re.search(r"「(\d{4})/(\d{2})/(\d{2})", html)
    play_iso = deadline = ""
    if m:
        cy, cmo, cd = int(m.group(1)), int(m.group(2)), int(m.group(3))
        conf = datetime.date(cy, cmo, cd)
        play = conf + datetime.timedelta(days=1)
        play_iso = play.isoformat()
        ctime = re.search(r"「\d{4}/\d{2}/\d{2}[^」]*?(\d{1,2}:\d{2})", html)
        deadline = f"{cmo:02d}/{cd:02d} " + (ctime.group(1) if ctime else "16:00")
    io   = re.search(r"\b(IN|OUT)\b", html)
    tee  = re.search(r"(\d{1,2}:\d{2})", html)        # first time on page = tee time
    minp = re.search(r"最低催行人数</span>\s*<b[^>]*>(\d+)名", html)
    jp   = re.search(r"海外住居者価格[：:]\s*[￥¥]?\s*([\d,]+)", html)
    en   = re.search(r"Overseas resident price:\s*([\d,]+)", html, re.I)
    sur  = re.search(r"２人プレー追加料金\s*([\d,]+)円", html)
    price = jp.group(1) if jp else (en.group(1) if en else None)

    # occupancy: one "b_blue03" name-cell per entrant; "no_entry" per empty seat
    names = [n.strip() for n in re.findall(r'class="iframe">([^<]+)<span class="f10">さん', html)]
    players = len(re.findall(r"b_blue03", html))
    empties = len(re.findall(r"no_entry", html))
    if players == 0 and names:        # fallback
        players = len(names)
    return {
        "date": play_iso, "deadline": deadline,
        "io": io.group(1) if io else "",
        "time": tee.group(1) if tee else "",
        "minPlayers": int(minp.group(1)) if minp else 2,
        "maxSeats": max(players + empties, 4) if (players + empties) else 4,
        "overseasPrice": int(price.replace(",", "")) if price else None,
        "surcharge2p": int(sur.group(1).replace(",", "")) if sur else None,
        "players": players,
        "ours": any(OURS in n for n in names),
    }

def main():
    print("Enumerating open plans ...")
    ozs = list_oz()
    print(f"  {len(ozs)} plans")
    slots = []
    for i, oz in enumerate(ozs, 1):
        try:
            d = parse_detail(get(f"{BASE}/plan.cfm?pid={PID}&rent_cid={RENT_CID}&oz={oz}&exh_flg=V"))
            d["id"] = oz
            if d["date"]:
                wd = datetime.date.fromisoformat(d["date"]).weekday()
                d["weekday"] = WEEK[wd]
            slots.append(d)
        except Exception as e:
            print(f"  [!] {oz} failed: {e}", file=sys.stderr)
        if i % 25 == 0:
            print(f"    {i}/{len(ozs)}")
        time.sleep(0.25)

    slots = [s for s in slots if s["date"]]
    # dedupe by physical slot (date + IN/OUT + time), keep first
    uniq, key_seen = [], set()
    for s in sorted(slots, key=lambda s: (s["date"], s["time"], s["io"])):
        k = (s["date"], s["io"], s["time"])
        if k in key_seen:
            continue
        key_seen.add(k); uniq.append(s)
    slots = uniq
    jst = datetime.timezone(datetime.timedelta(hours=9))
    payload = {
        "generatedAt": datetime.datetime.now(jst).strftime("%Y-%m-%d %H:%M") + " JST",
        "course": "Fuji Classic",
        "priceNote": "Overseas-golfer rate, lunch included.",
        "slots": slots,
    }
    with open(os.path.join(HERE, "data.js"), "w", encoding="utf-8") as f:
        f.write("window.FC_SLOTS = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n")
    json.dump(payload, open(os.path.join(HERE, "data.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    miss = sum(1 for s in slots if not s["overseasPrice"])
    ours = sum(1 for s in slots if s["ours"])
    print(f"[OK] {len(slots)} slots. overseas-price missing: {miss}. groups containing our booking: {ours}.")

if __name__ == "__main__":
    main()
