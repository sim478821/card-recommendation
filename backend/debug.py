import pdfplumber

# 테스트해볼 명세서 파일 이름을 정확히 넣어주세요. (backend 폴더 안에 있어야 합니다)
# 예: "현대카드 명세서.pdf" 또는 "KB국민은행 거래내역조회 명세서.pdf"
FILE_NAME = "KB국민은행 거래내역조회 명세서.pdf" 

print(f"\n🔍 [{FILE_NAME}] 파이썬 시력 검사 시작...\n" + "="*50)

try:
    with pdfplumber.open(FILE_NAME) as pdf:
        print(f"✅ 파일 열기 성공! (총 {len(pdf.pages)} 페이지)")
        
        page = pdf.pages[0]
        
        # 1. 텍스트 시력 검사
        text = page.extract_text()
        print("\n[1. 텍스트 추출 결과]")
        if text and text.strip():
            print(text[:500]) # 너무 길면 첫 500자만 출력
            print("... (이하 생략)")
        else:
            print("🚨 텅 비어있음! 파이썬이 글자를 전혀 읽지 못합니다. (보안 또는 이미지 PDF)")

        # 2. 표(Table) 시력 검사
        tables = page.extract_tables()
        print("\n[2. 표 추출 결과]")
        if tables:
            print(f"✅ 총 {len(tables)}개의 표를 찾았습니다. (첫 번째 표의 첫 2줄만 보여줍니다)")
            for row in tables[0][:2]:
                print(row)
        else:
            print("🚨 텅 비어있음! 파이썬이 표를 전혀 찾지 못했습니다.")

except Exception as e:
    print(f"🚨 파일 읽기 에러 발생: {e}")

print("="*50 + "\n")