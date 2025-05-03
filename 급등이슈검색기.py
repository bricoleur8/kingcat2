
import streamlit as st
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from collections import Counter

# ==========================
# 설정
# ==========================
STOPWORDS = ["공급", "계약", "실적", "투자", "기대감", "발표", "확정", "체결", "상승", "전망", "호재", "진행", "결정"]

# ==========================
# 엑셀 데이터 로드 및 전처리
# ==========================
@st.cache_data
def load_and_parse_excel(file):
    df_raw = pd.read_excel(file, sheet_name=0)
    df_raw.columns = ["종목코드", "종목명", "급등이력"]
    df_raw[["종목코드", "종목명"]] = df_raw[["종목코드", "종목명"]].ffill()

    parsed_rows = []
    for _, row in df_raw.iterrows():
        code = row["종목코드"]
        name = row["종목명"]
        raw_text = str(row["급등이력"])
        events = re.split(r'[\r\n\u2028\u000B]+', raw_text)
        i = 0
        while i < len(events) - 1:
            current = events[i].strip()
            next_line = events[i + 1].strip()
            if re.match(r"\d{4}/\d{2}/\d{2}", current):
                if len(next_line) > 5:
                    parsed_rows.append({
                        "종목명": name,
                        "종목코드": code,
                        "날짜": current,
                        "급등이슈": next_line
                    })
                i += 2
            else:
                i += 1
    return pd.DataFrame(parsed_rows)

# ==========================
# 최근 뉴스
# ==========================
def fetch_recent_news(keyword):
    base_url = "https://search.naver.com/search.naver"
    headers = {"User-Agent": "Mozilla/5.0"}
    today = datetime.today()
    one_week_ago = today - timedelta(days=7)
    params = {
        "where": "news",
        "query": keyword,
        "sort": "1",
        "pd": "3",
        "ds": one_week_ago.strftime('%Y.%m.%d'),
        "de": today.strftime('%Y.%m.%d'),
    }

    response = requests.get(base_url, headers=headers, params=params)
    soup = BeautifulSoup(response.text, "html.parser")
    news_items = soup.select("ul.list_news div.news_wrap.api_ani_send")
    results = []

    for item in news_items[:5]:
        title_tag = item.select_one("a.news_tit")
        summary_tag = item.select_one("div.dsc_wrap")
        source_tag = item.select_one("a.info_group")
        if title_tag and summary_tag:
            results.append({
                "제목": title_tag.text.strip(),
                "링크": title_tag["href"],
                "요약": summary_tag.text.strip(),
                "출처": source_tag.text.strip() if source_tag else "-"
            })
    return results

# ==========================
# 키워드 추출
# ==========================
def extract_keywords(texts, stopwords):
    word_list = []
    for text in texts:
        tokens = re.findall(r'[가-힣a-zA-Z0-9]+', text)
        word_list.extend([t for t in tokens if t not in stopwords and len(t) > 1])
    return Counter(word_list).most_common(10)

# ==========================
# Streamlit UI
# ==========================
st.set_page_config(page_title="급등이슈 검색기", layout="wide")
st.title("📈 급등주 이슈 검색기")

uploaded_file = st.file_uploader("📂 급등주 데이터 엑셀 파일 업로드", type=["xlsx"])

if uploaded_file:
    try:
        df = load_and_parse_excel(uploaded_file)
    except Exception as e:
        st.error("❌ 엑셀 파일을 불러오는 중 오류가 발생했습니다.")
        st.stop()

    keyword = st.text_input("🔍 종목명 또는 종목코드 입력", "")

    if keyword:
        filtered = df[df["종목명"].str.contains(keyword) | df["종목코드"].astype(str).str.contains(keyword)]

        st.markdown(f"### 🔎 검색 결과: <span style='color:green'>{keyword}</span>", unsafe_allow_html=True)
        st.dataframe(filtered, use_container_width=True)

        # 🔍 키워드 분석
        st.markdown("### 🧠 연관 키워드 분석")
        keywords = extract_keywords(filtered["급등이슈"], STOPWORDS)
        if keywords:
            keyword_df = pd.DataFrame(keywords, columns=["키워드", "빈도"])
            st.bar_chart(keyword_df.set_index("키워드"))
        else:
            st.info("분석 가능한 키워드가 없습니다.")

        # 🔁 같은 테마/이슈로 급등한 종목 비교
        st.markdown("### 📊 같은 테마/이슈로 급등한 종목 비교")
        if keywords:
            top_keyword = keywords[0][0]
            related = df[df["급등이슈"].str.contains(top_keyword)]
            st.dataframe(related, use_container_width=True)
        else:
            st.info("비교 가능한 종목이 없습니다.")

        # 📰 최근 뉴스 요약
        st.markdown("### 📰 최근 1주일 뉴스 요약")
        news_results = fetch_recent_news(keyword)
        if news_results:
            for news in news_results:
                st.markdown(f"**[{news['제목']}]({news['링크']})**")
                st.write(f"출처: {news['출처']}")
                st.write(news['요약'])
                st.markdown("---")
        else:
            st.info("최근 뉴스가 없습니다.")

        # 다운로드 버튼
        csv = filtered.to_csv(index=False).encode('utf-8-sig')
        st.download_button("🔵 검색 결과 다운로드 (CSV)", csv, file_name="급등이슈_검색결과.csv", mime="text/csv")

else:
    st.info("⬆️ `.xlsx` 파일을 업로드하면 급등 이슈 검색 기능을 사용할 수 있습니다.")
