import json
import requests
from bs4 import BeautifulSoup
import time

def rescue_card_names():
    try:
        with open('card_db.json', 'r', encoding='utf-8') as f:
            cards = json.load(f)
    except Exception as e:
        print("card_db.json 파일을 찾을 수 없습니다.", e)
        return

    print(f"🔍 총 {len(cards)}개의 카드 중 이름이 없는 카드를 찾아 복구합니다...")
    updated_count = 0

    for i, card in enumerate(cards):
        # card_name이 아예 없거나 빈칸("")인 경우에만 작동!
        if not card.get("card_name") or str(card.get("card_name")).strip() == "":
            card_id = card.get("card_id")
            if not card_id:
                continue

            # 카드고릴라 상세페이지(ID)로 다이렉트 접속
            url = f"https://www.card-gorilla.com/card/detail/{card_id}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

            try:
                res = requests.get(url, headers=headers, timeout=5)
                soup = BeautifulSoup(res.text, 'html.parser')

                # 웹페이지 상단의 탭 제목(<title>)에서 가장 정확한 카드 이름을 가져옵니다.
                page_title = soup.title.string if soup.title else ""

                if page_title:
                    # 예: "삼성 iD SELECT ALL 카드 - 카드고릴라" -> "삼성 iD SELECT ALL 카드"
                    real_name = page_title.split('-')[0].split('|')[0].strip()
                    card["card_name"] = real_name

                    # 만약 회사명도 "unknown"이라면, 카드 이름의 첫 단어(예: 삼성카드)로 복구!
                    if card.get("company") == "unknown":
                        card["company"] = real_name.split(' ')[0]

                    print(f"[{i+1}/{len(cards)}] 🎯 이름 복구 성공: {real_name}")
                    updated_count += 1
                else:
                    print(f"[{i+1}/{len(cards)}] ⚠️ 이름을 찾을 수 없음 (ID: {card_id})")

                # 카드고릴라 서버가 놀라지 않게 0.3초씩 쉬어줍니다.
                time.sleep(0.3) 
            except Exception as e:
                print(f"[{i+1}/{len(cards)}] ❌ 에러 발생 (ID {card_id}): {e}")

    # 복구 완료된 데이터를 원본 파일에 완벽하게 덮어쓰기
    if updated_count > 0:
        with open('card_db.json', 'w', encoding='utf-8') as f:
            json.dump(cards, f, ensure_ascii=False, indent=4)
        print(f"\n🎉 대성공! 총 {updated_count}개의 잃어버린 카드 이름을 모두 찾았습니다!")
    else:
        print("\n✔️ 비어있는 카드 이름이 없습니다. 데이터가 이미 완벽합니다.")

if __name__ == "__main__":
    rescue_card_names()