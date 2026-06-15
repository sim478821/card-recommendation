import pdfplumber
import re

class PDFStatementParser:
    def __init__(self, file_path):
        self.file_path = file_path

    def identify_company(self):
        try:
            with pdfplumber.open(self.file_path) as pdf:
                text = " ".join([p.extract_text() or "" for p in pdf.pages]).replace(" ", "").replace("\n", "")

                # ✅ KB국민은행 (계좌)
                if "계좌거래내역조회" in text:
                    return "KB국민은행"

                if "토스뱅크" in text: return "토스뱅크"
                if "신한" in text or "매입구분" in text: return "신한카드"
                if "KB국민" in text or "국민은행" in text: return "KB국민카드"
                if "현대" in text or "Hyundai" in text or "이용대금명세서" in text: return "현대카드"
                if "NH농협" in text or "농협" in text or "국내승인내역" in text: return "NH농협카드"
                return "기타"
        except:
            return "기타"

    def _extract_amount(self, text_amount):
        if not text_amount or str(text_amount) == 'None': return 0
        cleaned = re.sub(r'[^\d]', '', str(text_amount))
        return int(cleaned) if cleaned else 0

    def _clean_merchant(self, merchant):
        if str(merchant) == 'None': return ""
        ignore = ["체크", "신용", "결제확정", "일시불", "승인", "본인", "가족", "지역화폐", "할부", "취소", "가맹점명", "카드", "출금"]
        for w in ignore:
            merchant = merchant.replace(w, '')
        merchant = re.sub(r'[a-zA-Z0-9]{4,6}\*', '', merchant)
        merchant = re.sub(r'm ED2|하이패 스|하이패스|Kia|L |00\d{2}건|\d+건', '', merchant)
        merchant = re.sub(r'\s+', ' ', merchant).strip()
        return merchant

    def _clean_nh_merchant(self, text):
        text = str(text)
        text = re.sub(r'\d{4}[./-]\d{1,2}[./-]\d{1,2}', ' ', text)
        text = re.sub(r'\b\d{2}[./-]\d{1,2}[./-]\d{1,2}\b', ' ', text)
        text = re.sub(r'\d{2}:\d{2}(:\d{2})?', ' ', text)
        text = re.sub(r'\b\d{8}\b', ' ', text)
        text = re.sub(r'(?<!\d)(?:\d{1,3}(?:,\d{3})+)(?!\d)', ' ', text)
        text = re.sub(r'\b\d+\b', ' ', text)
        text = re.sub(r'\b[A-Z]\d{3}\b', ' ', text)
        ignore = ["체크", "신용", "결제확정", "일시불", "승인", "본인", "가족", "지역화폐", "할부", "취소", "가맹점명", "카드", "원", "건", "매입구분", "이용구분", "하이패스", "m ED2", "Kia", "L ", "출금"]
        for w in ignore:
            text = text.replace(w, ' ')
        text = re.sub(r'[^\w\s가-힣]', '', text)
        return re.sub(r'\s+', ' ', text).strip()

    def parse(self):
        company = self.identify_company()
        print(f"🔍 [분석 시작] 식별된 명세서: {company}")
        data = []
        seen = set()

        with pdfplumber.open(self.file_path) as pdf:
            for page in pdf.pages:

                # =========================================================
                # 🚨 0. KB국민은행 (🔥 완전 수정 핵심)
                # =========================================================
                if company == "KB국민은행":
                    text = page.extract_text() or ""

                    for line in text.split('\n'):
                        line = line.strip()
                        if not line:
                            continue

                        if not re.match(r'\d{4}\.\d{2}\.\d{2}', line):
                            continue

                        # 날짜 + 시간 제거
                        line = re.sub(r'^\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2}\s+', '', line)

                        # 금액 추출
                        amounts = re.findall(r'[\d,]+', line)
                        if len(amounts) < 2:
                            continue

                        withdraw = self._extract_amount(amounts[-3]) if len(amounts) >= 3 else 0
                        deposit = self._extract_amount(amounts[-2]) if len(amounts) >= 2 else 0

                        amount = withdraw if withdraw > 0 else 0

                        if amount <= 100:
                            continue

                        # merchant 추출
                        merchant_part = line
                        for amt in amounts:
                            merchant_part = merchant_part.replace(amt, '')

                        merchant_part = re.sub(r'-\s*\S+', '', merchant_part)
                        merchant = self._clean_merchant(merchant_part)

                        if len(merchant) < 2:
                            continue

                        if (merchant, amount) not in seen:
                            data.append({"merchant": merchant, "amount": amount})
                            seen.add((merchant, amount))

                    continue

                # =========================================================
                # 🚨 1. KB국민카드, 토스뱅크 (기존 유지)
                # =========================================================
                if company in ["KB국민카드", "토스뱅크"]:
                    text = page.extract_text() or ""
                    for line in text.split('\n'):
                        line = line.strip()

                        if company == "KB국민카드":
                            match_kb = re.search(r'(\d{4}\.\d{2}\.\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(\S+)\s+(.+?)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)', line)
                            if match_kb:
                                merchant = self._clean_merchant(match_kb.group(4))
                                amount = self._extract_amount(match_kb.group(5))
                                if amount > 100 and (merchant, amount) not in seen:
                                    data.append({"merchant": merchant, "amount": amount})
                                    seen.add((merchant, amount))
                            continue

                        if company == "토스뱅크":
                            match_toss = re.search(r'(-\d{1,3}(?:,\d{3})*)\s+[\d,]+\s+(.+)$', line)
                            if match_toss:
                                amount = self._extract_amount(match_toss.group(1))
                                merchant = self._clean_merchant(match_toss.group(2))
                                if amount > 100 and (merchant, amount) not in seen:
                                    data.append({"merchant": merchant, "amount": amount})
                                    seen.add((merchant, amount))
                            continue

                # =========================================================
                # 🚨 2. 신한, 현대카드 (기존 유지)
                # =========================================================
                if company in ["신한카드", "현대카드"]:
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            if not row or len(row) < 4: continue

                            if company == "신한카드" and len(row) >= 7 and row[0] and re.match(r'\d{4}\.\d{2}\.\d{2}', str(row[0])):
                                merchant = self._clean_merchant(str(row[3]))
                                amount = self._extract_amount(str(row[6]))
                                if amount > 100 and (merchant, amount) not in seen:
                                    data.append({"merchant": merchant, "amount": amount})
                                    seen.add((merchant, amount))
                                continue

                            if company == "현대카드" and len(row) >= 8:
                                if "이용가맹점" in str(row[2]) or not str(row[2]).strip() or str(row[2]) == 'None':
                                    continue
                                merchant = self._clean_merchant(str(row[2]))
                                amt_str = str(row[7]) if str(row[7]) != 'None' else str(row[3])
                                amount = self._extract_amount(amt_str)
                                if amount > 100 and (merchant, amount) not in seen:
                                    data.append({"merchant": merchant, "amount": amount})
                                    seen.add((merchant, amount))
                                continue

                # =========================================================
                # 🚨 3. NH농협카드 (기존 유지)
                # =========================================================
                if company == "NH농협카드":
                    try:
                        text = page.extract_text(layout=True)
                    except:
                        text = page.extract_text() or ""

                    if not text: continue

                    lines = text.split('\n')
                    for i, line in enumerate(lines):
                        line = line.strip()
                        if not line: continue

                        if any(w in line for w in ["총", "합계", "누적", "한도", "잔액", "최소결제", "전월", "조회", "대출", "연회비", "약정", "결제금액", "미결제", "연체", "이용대금", "선납", "수수료", "결제계좌", "기준일", "소계", "건수"]):
                            continue

                        amounts = re.findall(r'(?<!\d)(?:\d{1,3}(?:,\d{3})+)(?!\d)', line)
                        if not amounts: continue

                        int_amounts = [int(a.replace(',', '')) for a in amounts]
                        if not int_amounts: continue

                        amount = max(int_amounts)

                        if 100 < amount < 50000000:
                            start = max(0, i - 1)
                            end = min(len(lines), i + 2)
                            block = " ".join(lines[start:end])
                            merchant = self._clean_nh_merchant(block)

                            if len(merchant) >= 2:
                                data.append({"merchant": merchant, "amount": amount})

        return self._categorize_data(data)

    def _categorize_data(self, data):
        cat_map = {"온라인 쇼핑": 0, "오프라인 쇼핑": 0, "주유": 0, "식비": 0, "여가": 0}
        keywords = {
            "온라인 쇼핑": ["쿠팡", "네이버", "무신사", "지마켓", "11번가", "카카오", "스마일페이", "에이블리", "다날", "이니시스", "티몬"],
            "주유": ["주유", "충전", "가스", "GS", "SK", "에쓰오일", "오일"],
            "식비": ["식당", "카페", "스타벅스", "배달", "이마트", "맘스터치", "세븐일레븐", "CU", "우아한형제들", "요기요", "식육", "컴포즈", "빽다방"],
            "여가": ["영화", "여행", "숙박", "CGV", "호텔", "야놀자", "포토그레이", "상품권", "프린팅박스", "NICE"]
        }

        for item in data:
            found = False
            for cat, words in keywords.items():
                if any(w in item['merchant'] for w in words):
                    cat_map[cat] += item['amount']
                    found = True
                    break
            if not found:
                cat_map["오프라인 쇼핑"] += item['amount']

        print(f"✅ 최종 분류 결과: {cat_map}")
        return cat_map