# ======================= 라이브러리 임포트 ===================================================
import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import json
import folium

# 경고 메시지 숨기기
import warnings
warnings.filterwarnings('ignore')

# ======================= 페이지 세팅 ===================================================
# 페이지 설정
st.set_page_config(
    page_title="비일상적인 1인 소비 패턴 분석",
    page_icon=":bar_chart:",
    layout="wide"
)

# 제목
st.title(" :bar_chart: 비일상적인 1인 소비 패턴 분석", help="노마드 소비데이터를 통해 일상적인 상황이 아닌 경우의 서울시 1인 소비 패턴 분석합니다.")
st.caption("서울시 나홀로 소비 카드 데이터는 라이프스타일 지수를 개발하기 위해 생성된 데이터로 혼밥/혼커피 혹은 타 지역 음식점에서 결제한 서울시민의 카드 데이터입니다. 그 중에서 노마드 소비 데이터는 노마드 즉, ‘탐방’의 상황으로, 직장지, 주거지, 주 소비지를 제외하고 다른 행정구에서 발생한 카드 소비를 의미합니다.")
st.caption("노마드 소비데이터 분석을 통해서 일상적인 상황이 아닌 경우의 1인 소비 니즈와 패턴을 분석하고자 합니다.")

# ======================= 파일 업로더 ===================================================
geojson_file = 'LARD_ADM_SECT_SGG_11_202405.json'  # 서울특별시 행정구역 GeoJSON

# 데이터 읽기
data = pd.read_csv("노마드 소비데이터.csv", encoding="euc-kr")
date_preview = pd.read_csv("노마드 소비데이터.csv", encoding="euc-kr", parse_dates=['일별(DATE)'])

# 데이터 미리보기
st.subheader("🔎 노마드 소비데이터 미리보기", help="라이프스타일 지수를 개발하기 위해 생성된 데이터로 혼밥/혼커피 혹은 타 지역 음식점에서 결제한 서울시민의 카드 데이터입니다. 노마드 소비 데이터는 노마드 즉, ‘탐방’의 상황으로, 직장지, 주거지, 주 소비지를 제외하고 다른 행정구에서 발생한 카드 소비를 의미합니다.")
st.dataframe(date_preview.head())  # 데이터 미리보기

# ======================= 데이터 다운로드 ===================================================
# 다운로드 버튼 생성
csv = date_preview.to_csv(index=False, encoding="euc-kr").encode('euc-kr')

st.download_button(
    label="데이터 다운로드",
    data=csv,
    file_name="노마드_소비데이터.csv",  # 다운로드될 파일명
    mime="text/csv",
    help="클릭하면 해당 데이터가 CSV 파일로 다운로드됩니다."  # 도움말 표시
)

# ======================= 시작일 종료일 결정 ====================================================
# "시작일과 종료일을 선택해주세요" 메시지 출력
st.subheader("📅 시작일과 종료일을 선택해주세요.", help="기간: 2017/01/06 ~ 2019/12/29, 선택하지 않을 경우, 이 기간 전체에 대한 분석이 진행됩니다.")

# 화면을 2개의 컬럼으로 나누기
col1, col2 = st.columns(2)

# 일별(DATE)를 날짜형으로 변환
data["일별(DATE)"] = pd.to_datetime(data["일별(DATE)"], format='%Y%m%d')

# 시작일과 종료일 설정
startDate = data["일별(DATE)"].min()
endDate = data["일별(DATE)"].max()

# 시작일과 종료일을 선택
with col1:
    date1 = pd.to_datetime(st.date_input("시작일", startDate))

with col2:
    date2 = pd.to_datetime(st.date_input("종료일", endDate))

# 날짜에 따라 데이터프레임 필터링
data = data[(data["일별(DATE)"] >= date1) & (data["일별(DATE)"] <= date2)].copy()

# ======================= 사이드바 필터링 ===================================================
st.sidebar.header("📋 원하는 정보를 선택하세요.", help="선택한 고객주소 기준으로 소비 패턴을 분석합니다.")

# 카드이용금액 또는 카드이용건수 선택
selected_metric = st.sidebar.radio("원하는 분석 기준 선택", ("카드이용금액", "카드이용건수"), help="분석 목적에 따라 선택해주세요.")

# 시군구(고객주소 기준) 선택 단일선택 사이드바
selected_customregion = st.sidebar.selectbox("시군구(고객주소 기준) 선택", sorted(data['고객주소시군구(CUSTM_GU_NM)'].unique()), help="분석하고자 하는 시군구(고객주소 기준)를 선택해주세요.")
data_customregion = data[data['고객주소시군구(CUSTM_GU_NM)'] == selected_customregion]

# 시군구(가맹점 기준) 선택 다중선택 사이드바
selected_region = st.sidebar.multiselect("시군구(가맹점 기준) 선택(복수 가능)", sorted(data_customregion['가맹점주소시군구(STORE_GU_NM)'].unique()))

if not selected_region:  # 지역을 선택하지 않았을 때
    data_region = data_customregion.copy()  # 전체 데이터
else:
    data_region = data_customregion[data_customregion['가맹점주소시군구(STORE_GU_NM)'].isin(selected_region)]  # 선택한 지역 데이터만 필터링

# 성별 선택 다중선택 사이드바
selected_gender = st.sidebar.multiselect("성별 선택(복수 가능)", data_region['성별(GENDER)'].unique())

if not selected_gender:  # 성별을 선택하지 않았을 때
    data_gender = data_region.copy()  # 전체 데이터
else:
    data_gender = data_region[data_region['성별(GENDER)'].isin(selected_gender)]  # 선택한 성별 데이터만 필터링

# 연령대 리스트
age_groups = sorted(data_gender['연령대별(AGE_GR)'].unique())

# 연령대가 1개만 있을 때 기본값 설정
if len(age_groups) == 1:
    selected_age = age_groups[0]  # 하나만 선택되면 그 값이 기본값이 됨
else:
    selected_age = st.sidebar.select_slider(
        "연령대 선택",
        options=age_groups,  # 연령대 목록을 옵션으로 설정
        value=(age_groups[0], age_groups[-1]),  # 기본값: 전체 연령대
        help="슬라이드를 움직여서 연령대를 선택해주세요."
    )

# 선택된 연령대에 맞는 데이터 필터링
if isinstance(selected_age, tuple):  # 범위가 2개일 때 (튜플일 경우)
    data_age = data_gender[data_gender['연령대별(AGE_GR)'].between(selected_age[0], selected_age[1])]
else:  # 연령대가 1개만 선택된 경우
    data_age = data_gender[data_gender['연령대별(AGE_GR)'] == selected_age]

# 최종 선택된 데이터프레임
filtered_data = data_age

# ======================= 시군구(가맹점 기준)별 카드이용금액/카드이용건수 시각화 =====================================================
with st.container():
    col1, col2 = st.columns(2)

    # 시군구(가맹점 기준)별 카드이용금액/카드이용건수 지도
    with col1:
        st.subheader(f"🗺️ 시군구(가맹점 기준)별 {selected_metric}_지도", help="시군구(고객주소 기준) 필터만 적용한 지도입니다.")
        
        # 서울시청 중심 좌표
        city_hall = [37.566345, 126.977893]

        # 기본 지도 생성
        sigungu_map = folium.Map(
            location=city_hall,
            zoom_start=10,
            tiles='CartoDB positron'
        )

        # 고객주소 시군구별 카드 이용 금액/건수 집계
        if selected_metric == "카드이용금액":
            region_sales = data_customregion.groupby('가맹점주소시군구(STORE_GU_NM)')['카드이용금액(USE_AMT)'].sum().reset_index()
            region_sales.rename(columns={
                '가맹점주소시군구(STORE_GU_NM)': 'Region',
                '카드이용금액(USE_AMT)': 'Total Sales'
            }, inplace=True)
        else:  # 카드이용건수
            region_sales = data_customregion.groupby('가맹점주소시군구(STORE_GU_NM)')['카드이용건수(USE_CNT)'].sum().reset_index()
            region_sales.rename(columns={
                '가맹점주소시군구(STORE_GU_NM)': 'Region',
                '카드이용건수(USE_CNT)': 'Total Sales'
            }, inplace=True)

        # GeoJSON 파일 로드
        with open(geojson_file, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)

        # GeoJSON에서 '서울특별시 ' 제거
        for feature in geojson_data['features']:
            feature['properties']['SGG_NM'] = feature['properties']['SGG_NM'].replace('서울특별시 ', '')

        # 지역 이름 정리
        region_sales['Region'] = region_sales['Region'].str.strip()  # 공백 제거

        # GeoJSON에 존재하는 지역 이름과 일치시키기
        geo_regions = [feature['properties']['SGG_NM'] for feature in geojson_data['features']]
        region_sales = region_sales[region_sales['Region'].isin(geo_regions)]

        # Choropleth 맵 추가
        folium.Choropleth(
            geo_data=geojson_data,  # GeoJSON 파일
            data=region_sales,       # 데이터프레임
            columns=('Region', 'Total Sales'),  # Choropleth 매핑에 사용할 열
            key_on='feature.properties.SGG_NM',  # GeoJSON의 속성과 매핑
            fill_color='YlGnBu',           # 색상 Yellow-Green-Blue
            fill_opacity=0.7,              # 채우기 투명도
            line_opacity=0.5,              # 경계선 투명도
            legend_name=f'시군구별 {selected_metric}',  # 범례 이름
            nan_fill_color='rgba(0,0,0,0)',  # 데이터가 없는 부분은 투명
            nan_fill_opacity=0  # 데이터가 없는 부분을 완전히 투명하게
        ).add_to(sigungu_map)
        
        # 툴팁 추가 (각 지역의 정보 표시)
        folium.GeoJson(
            geojson_data,
            tooltip=folium.GeoJsonTooltip(
                fields=['SGG_NM'],
                aliases=['가맹점 위치:'],
                localize=True
            )
        ).add_to(sigungu_map)
        
        # CSS 스타일을 통해 테두리 제거 (folium 내부 스타일)
        for feature in geojson_data['features']:
            feature['properties']['style'] = {'color': 'transparent', 'weight': 0}  # 지도 경계선 색상 제거

        # 지도 객체 생성
        map_html = sigungu_map._repr_html_()
        
        # Streamlit에서 HTML로 지도 표시
        st.components.v1.html(map_html, width=700, height=500)
        
    # 시군구(가맹점 기준)별 카드이용금액/카드이용건수 원형차트
    with col2:
        st.subheader(f"📊 시군구(가맹점 기준)별 {selected_metric}_%")
        if selected_metric == "카드이용금액":
            fig = px.pie(
                filtered_data, 
                values = '카드이용금액(USE_AMT)', 
                names = '가맹점주소시군구(STORE_GU_NM)', 
                hole = 0.5
            )
        else:  # 카드이용건수
            fig = px.pie(
                filtered_data, 
                values = '카드이용건수(USE_CNT)', 
                names = '가맹점주소시군구(STORE_GU_NM)', 
                hole = 0.5
            )
        fig.update_traces(
            text = filtered_data['가맹점주소시군구(STORE_GU_NM)'],
            textposition = "outside"
        )
        st.plotly_chart(fig, use_container_width=True)

    # 시군구(가맹점 기준)별 데이터 보기 및 다운로드 기능
    with st.expander(f"시군구(가맹점 기준)별 {selected_metric} 데이터 보기"):
        if selected_metric == "카드이용금액":
            region = filtered_data.groupby(   # 지역별 판매액 계산
                by = '가맹점주소시군구(STORE_GU_NM)',              # 지역별 그룹화
                as_index = False            # 인덱스 사용 안함
                )['카드이용금액(USE_AMT)'].sum()            # 판매액 합계
        else:  # 카드이용건수
            region = filtered_data.groupby(   # 지역별 카드이용건수 계산
                by = '가맹점주소시군구(STORE_GU_NM)',              # 지역별 그룹화
                as_index = False            # 인덱스 사용 안함
                )['카드이용건수(USE_CNT)'].sum()            # 이용건수 합계
        
        st.dataframe(region.style.background_gradient(cmap="Blues"))  # 데이터프레임 출력
        csv = region.to_csv(index = False).encode('utf-8')   # 데이터프레임을 csv로 변환
        st.download_button(
            f"시군구(가맹점 기준)별 {selected_metric} 데이터 다운로드", 
            data = csv, 
            file_name = f"Gu_{selected_metric}.csv", 
            mime = "text/csv",
            help = '클릭하면 해당 데이터가 CSV 파일로 다운로드됩니다.'
        )

# ======================= 연령대별 카드이용금액/카드이용건수 분석 ===================================================
import streamlit as st
import plotly.express as px
import pandas as pd

# 선택된 메트릭에 따라 데이터 그룹화
st.subheader(f"📈 연령대별 {selected_metric}", help="시군구(고객주소 기준) 필터만 적용한 그래프입니다.")

if selected_metric == "카드이용금액":
    sales_by_age = data_customregion.groupby(['연령대별(AGE_GR)'])['카드이용금액(USE_AMT)'].sum().reset_index()
    y_axis = '카드이용금액(USE_AMT)'
    y_label = '카드이용금액'
elif selected_metric == "카드이용건수":
    sales_by_age = data_customregion.groupby(['연령대별(AGE_GR)'])['카드이용건수(USE_CNT)'].sum().reset_index()
    y_axis = '카드이용건수(USE_CNT)'
    y_label = '카드이용건수'

# 시각화: 꺾은선 그래프
fig_line = px.line(
    sales_by_age,
    x='연령대별(AGE_GR)',
    y=y_axis,
    markers=True,
    template='plotly_white',
    labels={'연령대별(AGE_GR)': '연령대', y_axis: y_label},
)

# 연령대 정렬
fig_line.update_xaxes(categoryorder='array', categoryarray=sorted(sales_by_age['연령대별(AGE_GR)'].unique()))

# 그래프 출력
st.plotly_chart(fig_line, use_container_width=True)

# ======================= 데이터 보기 및 이미지/다운로드 기능 추가 =====================================================
with st.expander(f"연령대별 {selected_metric} 데이터 보기"):
    # 연령대별 카드이용금액/카드이용건수 합계 계산
    region_age = filtered_data.groupby(
        by=['연령대별(AGE_GR)'],  # 연령대별 그룹화
        as_index=False
    )[y_axis].sum()  # 선택된 메트릭 합계

    # 데이터프레임 출력
    st.dataframe(region_age.style.background_gradient(cmap="Blues"))  # 스타일 추가하여 출력

    # 데이터프레임을 CSV로 변환
    csv = region_age.to_csv(index=False).encode('utf-8')

    # 다운로드 버튼 추가
    st.download_button(
        f"연령대별 {selected_metric} 데이터 다운로드", 
        data=csv, 
        file_name=f"Age_{selected_metric}_Line.csv", 
        mime="text/csv",
        help='클릭하면 해당 데이터가 CSV 파일로 다운로드됩니다.'
    )

# ======================= 업종별 연령대별 카드이용금액/카드이용건수 분석 ===================================================
st.subheader(f"📊 업종별 연령대별 {selected_metric}")

# 선택한 메트릭에 따라 그룹화
if selected_metric == "카드이용금액":
    sales_by_category_age = filtered_data.groupby(['업종(UPJONG_NM)', '연령대별(AGE_GR)'])['카드이용금액(USE_AMT)'].sum().reset_index()
    y_axis = '카드이용금액(USE_AMT)'
    y_label = '카드이용금액'
elif selected_metric == "카드이용건수":
    sales_by_category_age = filtered_data.groupby(['업종(UPJONG_NM)', '연령대별(AGE_GR)'])['카드이용건수(USE_CNT)'].sum().reset_index()
    y_axis = '카드이용건수(USE_CNT)'
    y_label = '카드이용건수'

# 시각화
fig_category_age = px.bar(
    sales_by_category_age,
    x='업종(UPJONG_NM)',
    y=y_axis,
    color='연령대별(AGE_GR)',
    text=y_axis,
    template='plotly_white',
    labels={'업종(UPJONG_NM)': '업종', y_axis: y_label, '연령대별(AGE_GR)': '연령대'},
    category_orders={'연령대별(AGE_GR)': sorted(sales_by_category_age['연령대별(AGE_GR)'].unique())}  # 연령대 자동 정렬
)

# 그래프 출력
st.plotly_chart(fig_category_age, use_container_width=True)

# ======================= 데이터 보기 및 이미지/다운로드 기능 추가 =====================================================
with st.expander(f"업종별 연령대별 {selected_metric} 데이터 보기"):
    # 업종별, 연령대별 카드이용금액/카드이용건수 합계 계산
    region_age = filtered_data.groupby(
        by=['업종(UPJONG_NM)', '연령대별(AGE_GR)'],  # 업종, 연령대별 그룹화
        as_index=False
    )[y_axis].sum()  # 선택된 메트릭 합계

    # 데이터프레임 출력
    st.dataframe(region_age.style.background_gradient(cmap="Blues"))  # 스타일 추가하여 출력

    # 데이터프레임을 CSV로 변환
    csv = region_age.to_csv(index=False).encode('utf-8')

    # 다운로드 버튼 추가
    st.download_button(
        f"업종별 연령대별 {selected_metric} 데이터 다운로드", 
        data=csv, 
        file_name=f"Upjong_Age_{selected_metric}.csv", 
        mime="text/csv",
        help='클릭하면 해당 데이터가 CSV 파일로 다운로드됩니다.'
    )

# ======================= 데이터 다운로드 ===================================================
st.subheader("⬇️ 필터링한 데이터 다운로드", help="카드이용금액과 카드이용건수 데이터를 모두 포함합니다.")
st.dataframe(filtered_data.head(10))

csv = filtered_data.to_csv(index=False).encode('utf-8')
st.download_button(
    label="데이터 다운로드",
    data=csv,
    file_name="filtered_data.csv",
    mime="text/csv",
    help="클릭하면 해당 데이터가 CSV 파일로 다운로드됩니다."
)
