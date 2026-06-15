import itertools
import re

def parse_fee(fee_str):
    if "전체" in fee_str: return float('inf')
    if "0원" in fee_str: return 0
    if "1만원" in fee_str: return 10000
    if "3만원" in fee_str: return 30000
    if "5만원" in fee_str: return 50000
    if "10만원" in fee_str and "이상" not in fee_str: return 100000
    return float('inf') 

def parse_performance(perf_str):
    if "전체" in perf_str: return float('inf')
    if "0원" in perf_str: return 0
    if "30만원" in perf_str: return 300000
    if "50만원" in perf_str and "이상" not in perf_str: return 500000
    return float('inf')

def extract_first_number(val_str):
    if not val_str: return 0.0
    cleaned = str(val_str).replace(',', '')
    matches = re.findall(r'\d+(?:\.\d+)?', cleaned)
    return float(matches[0]) if matches else 0.0

def extract_limit_number(val_str):
    if not val_str or str(val_str) in ["없음", "무제한", "무한"]: return 0.0
    cleaned = str(val_str).replace(',', '')
    matches = re.findall(r'\d+', cleaned)
    if not matches: return 0.0
    
    nums = [float(m) for m in matches]
    max_num = max(nums)
    
    if "만" in cleaned and max_num < 1000:
        return max_num * 10000
    if max_num < 1000: 
        return 0.0 
    return max_num

def calc_card_savings(card, user_spending):
    savings = {k: 0 for k in user_spending.keys()}
    
    for benefit in card.get("benefits", []):
        cat = str(benefit.get("category", ""))
        keywords = " ".join(benefit.get("keywords", [])) if isinstance(benefit.get("keywords"), list) else ""
        note = str(benefit.get("note", ""))
        
        full_text = f"{cat} {keywords} {note}"
        full_text_nospace = full_text.replace(" ", "")
        
        target_cat = None
        
        if any(w in full_text_nospace for w in ["온라인", "배달", "이커머스", "쿠팡", "네이버", "인터넷", "앱"]): target_cat = "온라인 쇼핑"
        elif any(w in full_text_nospace for w in ["오프라인", "마트", "편의점", "슈퍼", "백화점", "다이소"]): target_cat = "오프라인 쇼핑"
        elif "쇼핑" in full_text: target_cat = "온라인 쇼핑" 
        elif any(w in full_text_nospace for w in ["주유", "교통", "택시", "버스", "가스", "차량"]): target_cat = "주유"
        elif any(w in full_text_nospace for w in ["식비", "커피", "음식", "카페", "식당", "푸드", "베이커리"]): target_cat = "식비"
        elif any(w in full_text_nospace for w in ["여가", "영화", "여행", "숙박", "문화", "항공"]): target_cat = "여가"
        
        if not target_cat: continue
        
        spent = int(user_spending.get(target_cat, 0))
        if spent == 0: continue
        
        val = extract_first_number(benefit.get("discount_value", ""))
        limit = extract_limit_number(benefit.get("monthly_limit", ""))
        
        if limit <= 0 or limit > 50000: 
            limit = 15000 
            
        dtype = str(benefit.get("discount_type", "")).lower()
        val_str = str(benefit.get("discount_value", ""))
        
        is_percent = "percent" in dtype or "%" in val_str
            
        if is_percent:
            if val >= 50: val = 10 # 50% 이상 할인은 현실성이 떨어지므로 10%로 강제 조정
            if val < 1:  
                save = int(spent * val)
            else:        
                save = int((spent * val) / 100)
        else:
            if val > 50000: val = 5000 
            save = int(val) 
            
        # 🚨 [가장 현실적인 절대 방어막]
        # 추출된 할인 금액이 아무리 커도, 실제 사용 금액 대비 '현실적인 최대 할인율'을 넘지 못하게 억제합니다!
        # 주유는 현실적으로 최대 10% 한계, 나머지 카테고리는 최대 30%로 제한합니다.
        max_realistic_save = int(spent * 0.10) if target_cat == "주유" else int(spent * 0.30)
        save = min(save, max_realistic_save)
            
        current_save = min(save, int(limit))
        if current_save > savings[target_cat]:
            savings[target_cat] = current_save
            
    for k in savings:
        savings[k] = int(min(savings[k], int(user_spending[k])))
        
    return savings

def get_best_combinations(user_spending, user_filters, card_database):
    target_company = user_filters.get("cardCompany", "전체 카드사")
    max_fee = parse_fee(user_filters.get("annualFee", "전체 연회비"))
    max_perf = parse_performance(user_filters.get("performance", "전체 전월실적"))
    
    filtered_cards = []
    seen_card_names = set()
    
    for i, card in enumerate(card_database):
        raw_name = card.get("card_name") or card.get("name") or card.get("title") or ""
        raw_name = str(raw_name).strip()
        
        if not raw_name:
            card_id = card.get("card_id", f"미상_{i+1}")
            raw_name = f"카드_{card_id}"
            
        card["fixed_name"] = raw_name
        
        if target_company != "전체 카드사" and target_company not in str(card.get("company", "")):
            continue
        if max_fee != float('inf') and extract_first_number(card.get("annual_fee")) > max_fee:
            continue
        if max_perf != float('inf') and extract_first_number(card.get("required_previous_performance")) > max_perf:
            continue
            
        if card["fixed_name"] not in seen_card_names:
            seen_card_names.add(card["fixed_name"])
            filtered_cards.append(card)

    if len(filtered_cards) < 2:
        filtered_cards = []
        for i, card in enumerate(card_database):
            raw_name = card.get("card_name") or card.get("name") or card.get("title") or ""
            raw_name = str(raw_name).strip()
            if not raw_name:
                card_id = card.get("card_id", f"미상_{i+1}")
                raw_name = f"카드_{card_id}"
            card["fixed_name"] = raw_name
            filtered_cards.append(card)

    for card in filtered_cards:
        card["calculated_savings"] = calc_card_savings(card, user_spending)
        card["total_save"] = sum(card["calculated_savings"].values())

    top_candidates = sorted(filtered_cards, key=lambda x: x["total_save"], reverse=True)[:50]
    
    if len(top_candidates) < 2:
        return [{
            "id": "combo_error",
            "cards": ["데이터 분석 오류", "적합한 카드를 찾지 못했습니다."],
            "totalDiscount": 0,
            "chartData": [{"category": "결과 없음", "beforeDiscount": 0, "afterDiscount": 0}]
        }]

    best_combinations = []
    for card1, card2 in itertools.combinations(top_candidates, 2):
        combined_total = 0
        chart_data = []
        
        for cat, spent in user_spending.items():
            spent_int = int(spent)
            saved_a = int(card1["calculated_savings"].get(cat, 0))
            saved_b = int(card2["calculated_savings"].get(cat, 0))
            
            total_cat_save = int(min(saved_a + saved_b, spent_int))
            combined_total += total_cat_save
            
            chart_data.append({
                "category": cat,
                "beforeDiscount": spent_int,
                "afterDiscount": spent_int - total_cat_save
            })
            
        best_combinations.append({
            "cards": [card1["fixed_name"], card2["fixed_name"]],
            "totalDiscount": combined_total,
            "chartData": chart_data
        })

    sorted_combinations = sorted(best_combinations, key=lambda x: x["totalDiscount"], reverse=True)
    final_top_5 = []
    card_appearance_count = {}
    
    for combo in sorted_combinations:
        c1, c2 = combo["cards"]
        if card_appearance_count.get(c1, 0) >= 2 or card_appearance_count.get(c2, 0) >= 2:
            continue
        final_top_5.append(combo)
        card_appearance_count[c1] = card_appearance_count.get(c1, 0) + 1
        card_appearance_count[c2] = card_appearance_count.get(c2, 0) + 1
        if len(final_top_5) >= 5:
            break

    if len(final_top_5) < 5:
        for combo in sorted_combinations:
            if combo not in final_top_5:
                final_top_5.append(combo)
            if len(final_top_5) >= 5:
                break

    for i, combo in enumerate(final_top_5):
        combo["id"] = f"combo_{i+1}"

    return final_top_5