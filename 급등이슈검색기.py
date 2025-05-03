import streamlit as st
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# 엑셀 데이터 로드 및 전처리 함수
def load_and_parse_excel(file):
    df_raw = pd.read_excel(file, sheet_name=0)
    df_raw.columns = ["종목코드", "종목명", "급등이력", "기타"]
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

# 최근 1주일 뉴스 가져오기
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

# Streamlit UI
st.set_page_config(page_title="급등이슈 검색기", layout="wide")
st.title("📈 급등주 이슈 검색기")

uploaded_file = st.file_uploader("📂 급등주 데이터 엑셀 파일 업로드", type=["xlsx"])

if uploaded_file:
    df = load_and_parse_excel(uploaded_file)
    keyword = st.text_input("🔍 종목명 또는 종목코드 입력", "")

    if keyword:
        filtered = df[df["종목명"].str.contains(keyword) | df["종목코드"].astype(str).str.contains(keyword)]
        st.write(f"### 🔎 검색 결과: `{keyword}`")
        st.dataframe(filtered, use_container_width=True)

        # 연관 키워드 분석
        st.write("### 🧠 연관 키워드 분석")
        common_keywords = filtered['급등이슈'].str.extractall(r'(반도체|로봇|공급계약|상장|실적|메모리|투자|AI|전기차|수출|FDA|임상)')[0].value_counts()
        if not common_keywords.empty:
            st.bar_chart(common_keywords)
        else:
            st.info("분석 가능한 키워드가 없습니다.")

        # 뉴스 요약
        st.write("### 📰 최근 1주일 뉴스 요약")
        news_results = fetch_recent_news(keyword)
        if news_results:
            for news in news_results:
                st.markdown(f"**[{news['제목']}]({news['링크']})**")
                st.write(f"출처: {news['출처']}")
                st.write(news['요약'])
                st.markdown("---")
        else:
            st.info("최근 뉴스가 없습니다.")

        # 다운로드
        csv = filtered.to_csv(index=False).encode('utf-8-sig')
        st.download_button("⬇️ 검색 결과 다운로드 (CSV)", csv, file_name="급등이슈_검색결과.csv", mime="text/csv")

else:
    st.info("⬆️ 왼쪽 상단에서 `.xlsx` 파일을 업로드하면 급등 이슈 검색 기능을 사용할 수 있습니다.")
