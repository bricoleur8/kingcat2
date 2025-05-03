import streamlit as st
import pandas as pd
import re
import io
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# Streamlit UI 설정
st.set_page_config(page_title="급등주 이슈 검색기", layout="wide")
st.title("📈 급등주 이슈 검색기")

# 파일 업로드
uploaded_file = st.file_uploader("급등주 데이터 엑셀 파일 업로드", type=["xlsx"])

@st.cache_data
def parse_excel(file):
    df_raw = pd.read_excel(file, engine="openpyxl")
    df_raw.columns = [str(c).strip() for c in df_raw.columns]
    df_raw[["종목코드", "종목명"]] = df_raw[["종목코드", "종목명"]].ffill()

    rows = []
    for _, row in df_raw.iterrows():
        code, name = row["종목코드"], row["종목명"]
        raw_text = str(row["급등이력"])
        events = re.split(r'[\r\n\u2028\u000B]+', raw_text)
        i = 0
        while i < len(events) - 1:
            date_line = events[i].strip()
            issue_line = events[i + 1].strip()
            if re.match(r"\d{4}/\d{2}/\d{2}", date_line):
                rows.append({"종목명": name, "종목코드": code, "날짜": date_line, "급등이슈": issue_line})
                i += 2
            else:
                i += 1
    return pd.DataFrame(rows)

# 뉴스 수집 함수
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
    res = requests.get(base_url, headers=headers, params=params)
    soup = BeautifulSoup(res.text, "html.parser")
    items = soup.select("ul.list_news div.news_wrap.api_ani_send")
    news = []
    for item in items[:5]:
        title = item.select_one("a.news_tit")
        desc = item.select_one("div.dsc_wrap")
        if title and desc:
            news.append({
                "제목": title.text.strip(),
                "링크": title["href"],
                "요약": desc.text.strip()
            })
    return news

# 메인 기능
if uploaded_file:
    df = parse_excel(uploaded_file)
    keyword = st.text_input("종목명 또는 종목코드 입력")

    if keyword:
        filtered = df[df["종목명"].str.contains(keyword) | df["종목코드"].astype(str).str.contains(keyword)]

        st.write(f"### 🔍 검색 결과 - `{keyword}` 관련 급등 이슈")
        st.dataframe(filtered, use_container_width=True)

        st.write("### 📌 동일 이슈 또는 테마 관련 종목")
        common_issues = filtered["급등이슈"].unique()
        related = df[df["급등이슈"].isin(common_issues)]
        st.dataframe(related, use_container_width=True)

        st.write("### 🔎 해당 키워드를 포함한 모든 이슈")
        keyword_related = df[df["급등이슈"].str.contains(keyword, na=False)]
        st.dataframe(keyword_related, use_container_width=True)

        st.write("### 🗞️ 최근 1주일 뉴스 요약")
        news = fetch_recent_news(keyword)
        if news:
            for item in news:
                st.markdown(f"- [{item['제목']}]({item['링크']})")
                st.write(item['요약'])
        else:
            st.info("관련 뉴스가 없습니다.")
else:
    st.info("📁 엑셀 파일(.xlsx)을 업로드하세요.")
