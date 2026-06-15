from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import copy  # 🚨 [핵심 추가] 메모리 복사를 위한 라이브러리
import firebase_admin
from firebase_admin import credentials, firestore

from parser import PDFStatementParser
from recommend import get_best_combinations

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Firebase 초기화
fb_path = os.path.join(BASE_DIR, "firebase_key.json")
try:
    if os.path.exists(fb_path):
        cred = credentials.Certificate(fb_path)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        rankings_ref = db.collection('card_rankings')
    else:
        db = None
except Exception as e:
    print(f"🚨 Firebase 초기화 실패: {e}")
    db = None

# 무적의 JSON 로더
def load_json_safe(file_path):
    if not os.path.exists(file_path):
        return [], "파일이 존재하지 않습니다."
    
    encodings = ['utf-8', 'utf-8-sig', 'cp949', 'euc-kr']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                data = json.load(f)
                extracted_cards = []
                
                if isinstance(data, list):
                    extracted_cards = data
                elif isinstance(data, dict):
                    for k, v in data.items():
                        if isinstance(v, list):
                            extracted_cards.extend(v)
                    if not extracted_cards:
                        for k, v in data.items():
                            if isinstance(v, dict):
                                extracted_cards.append(v)
                    if not extracted_cards:
                        extracted_cards = [data]
                        
                return extracted_cards, f"✅ {enc} 로드 성공 (총 {len(extracted_cards)}개)"
                
        except json.JSONDecodeError as e:
            if enc == 'utf-8':
                return [], f"JSON 문법 오류: {e}"
        except UnicodeDecodeError:
            continue
        except Exception as e:
            return [], f"알 수 없는 오류: {e}"
            
    return [], "파일을 읽을 수 없습니다."

db_path = os.path.join(BASE_DIR, "card_db.json")
card_database, db_msg = load_json_safe(db_path)
print(f"📊 DB 로드 상태: {db_msg}")

@app.post("/api/analyze")
def analyze_statement(file: UploadFile = File(...), filters: str = Form(...)):
    file_path = f"temp_{file.filename}"
    
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())
        
        parser = PDFStatementParser(file_path)
        user_spending = parser.parse() 
        
    except Exception as e:
        print(f"❌ 분석 중 시스템 에러 발생: {e}")
        return {"error": "서버 내부에서 명세서를 처리하는 중 오류가 발생했습니다."}
        
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
    
    if "error" in user_spending:
        return {"error": user_spending["error"]}

    if not card_database:
        return {
            "summary": user_spending,
            "recommendations": [{
                "id": "error_db",
                "cards": ["데이터 로드 실패 🚨", "JSON 파일 확인 필요"],
                "totalDiscount": 0,
                "chartData": [{"category": f"{db_msg}", "beforeDiscount": 0, "afterDiscount": 0}]
            }]
        }

    # 🚨 [가장 중요한 수정] 전역 변수인 card_database가 이전 계산(10만원)으로 오염된 것을 완벽히 차단하고
    # 매 요청마다 순수한 깨끗한 복사본을 만들어 recommend에 전달합니다!
    clean_card_database = copy.deepcopy(card_database)

    user_filters = json.loads(filters)
    top_5_recommendations = get_best_combinations(user_spending, user_filters, clean_card_database)

    # Firebase 저장 로직
    if db:
        for combo in top_5_recommendations:
            for card_name in combo["cards"]:
                try:
                    safe_doc_id = card_name.replace("/", "_").replace("\\", "_").strip()
                    card_doc = rankings_ref.document(safe_doc_id)
                    doc_snap = card_doc.get()
                    if doc_snap.exists:
                        card_doc.update({"count": firestore.Increment(1)})
                    else:
                        card_doc.set({"name": card_name, "count": 1})
                except Exception as fb_err:
                    print(f"⚠️ Firebase 랭킹 반영 실패 ({card_name}): {fb_err}")

    return {
        "summary": user_spending,
        "recommendations": top_5_recommendations
    }

@app.get("/api/rankings")
def get_popular_rankings():
    if not db: return []
    try:
        docs = rankings_ref.order_by("count", direction=firestore.Query.DESCENDING).limit(10).stream()
        return [{"id": i, "name": d.to_dict().get("name"), "count": d.to_dict().get("count")} for i, d in enumerate(docs, 1)]
    except:
        return []