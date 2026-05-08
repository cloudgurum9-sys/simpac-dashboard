import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import io
import datetime

# --- 페이지 기본 설정 (공통) ---
st.set_page_config(
    page_title="SIMPAC 통합 회계/재무 대시보드 포트폴리오",
    page_icon="💼",
    layout="wide"
)

# ==============================================================================
# [프로젝트 1] 내부통제 및 이상치 탐지 로직
# ==============================================================================
def run_project1():
    st.title("⚙️ SIMPAC 회계팀 지출증빙 및 내부통제 자동 검증 시스템")
    st.markdown("""
    **[채용전환형 인턴 포트폴리오 - 프로젝트 1]**  
    사내 ERP(지출결의) 데이터와 카드사 실승인 데이터를 대사(Reconciliation)하여 **미증빙, 금액 불일치, 내부규정 위반 결제**를 자동으로 탐지합니다.
    """)

    @st.cache_data
    def generate_simpac_data():
        np.random.seed(42)
        n_rows = 500
        
        bu_list = ['프레스 BU', '메탈 BU', 'ENG BU', '산업기계 BU', '리스텍비즈 BU']
        merchant_list = ['사무용품(알파)', '일반식당', '주유소', '골프장(규정위반)', '유흥주점(규정위반)', '상품권(규정위반)', 'KT(통신비)', '항공권']
        
        # 1) ERP 지출결의 데이터
        erp_data = pd.DataFrame({
            '결의번호': [f'ERP-{2025000+i}' for i in range(n_rows)],
            '사업부': np.random.choice(bu_list, n_rows),
            '기안자': [f'사원_{i}' for i in range(n_rows)],
            '사용일자': [datetime.date(2025, 4, 1) + datetime.timedelta(days=int(d)) for d in np.random.randint(0, 30, n_rows)],
            '거래처': np.random.choice(merchant_list, n_rows, p=[0.3, 0.4, 0.1, 0.05, 0.05, 0.05, 0.03, 0.02]),
            'ERP청구액': np.random.randint(1, 100, n_rows) * 10000
        })
        
        # 2) 카드사 실제 승인 데이터
        card_data = erp_data.copy()
        drop_indices = np.random.choice(card_data.index, 10, replace=False) # 미증빙
        card_data = card_data.drop(drop_indices)
        
        mismatch_indices = np.random.choice(card_data.index, 15, replace=False) # 금액불일치
        card_data.loc[mismatch_indices, 'ERP청구액'] = card_data.loc[mismatch_indices, 'ERP청구액'] + 5000 
        card_data.rename(columns={'ERP청구액': '카드승인액'}, inplace=True)
        
        # 3) 데이터 병합
        merged_df = pd.merge(erp_data, card_data[['결의번호', '카드승인액']], on='결의번호', how='left')
        
        merged_df['이상치_유형'] = '정상'
        merged_df['위험도'] = 0
        
        def detect_anomaly(row):
            anomalies = []
            risk = 0
            
            if pd.isna(row['카드승인액']):
                anomalies.append('미증빙(누락)')
                risk += 3
            elif row['ERP청구액'] != row['카드승인액']:
                anomalies.append('금액 불일치')
                risk += 2
            
            if '위반' in row['거래처']:
                anomalies.append('의심 거래처')
                risk += 5
                
            if row['사용일자'].weekday() >= 5:
                anomalies.append('주말 사용')
                risk += 4
                
            if not anomalies:
                return pd.Series(['정상', 0])
            else:
                return pd.Series([', '.join(anomalies), risk])
                
        merged_df[['이상치_유형', '위험도']] = merged_df.apply(detect_anomaly, axis=1)
        merged_df = merged_df.sort_values(by='위험도', ascending=False).reset_index(drop=True)
        return merged_df

    df = generate_simpac_data()
    
    st.markdown("### 🔍 검색 필터")
    selected_bu = st.multiselect("[내부통제] 사업부(BU) 선택", options=df['사업부'].unique(), default=df['사업부'].unique())

    filtered_df = df[df['사업부'].isin(selected_bu)]
    filtered_anomalies = filtered_df[filtered_df['이상치_유형'] != '정상']

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 지출결의 검토 건수", f"{len(filtered_df):,}건")
    with col2:
        st.metric("🚨 이상치 적발 건수", f"{len(filtered_anomalies):,}건")
    with col3:
        risk_rate = (len(filtered_anomalies) / len(filtered_df)) * 100 if len(filtered_df) > 0 else 0
        st.metric("내부통제 위반율", f"{risk_rate:.1f}%")
    with col4:
        total_risk_amt = filtered_anomalies['ERP청구액'].sum()
        st.metric("위반 의심 총 금액", f"₩{total_risk_amt:,.0f}")

    st.divider()

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.subheader("🏢 사업부별 내부통제 위반 건수")
        bu_risk_counts = filtered_anomalies['사업부'].value_counts().reset_index()
        bu_risk_counts.columns = ['사업부', '건수']
        fig1 = px.bar(bu_risk_counts, x='사업부', y='건수', text='건수', color='사업부', template='plotly_white')
        st.plotly_chart(fig1, use_container_width=True)

    with col_chart2:
        st.subheader("⚠️ 이상치 유형별 분포 (위험도 순)")
        all_types = filtered_anomalies['이상치_유형'].str.split(', ').explode()
        type_counts = all_types.value_counts().reset_index()
        type_counts.columns = ['유형', '건수']
        fig2 = px.pie(type_counts, values='건수', names='유형', hole=0.4, template='plotly_white')
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    st.subheader("📋 이상 거래 상세 내역 (Risk Score 순)")

    def highlight_risk(val):
        if val >= 5: return 'background-color: #ffcccc' 
        elif val >= 3: return 'background-color: #fff2cc' 
        return ''

    # [수정 완료] applymap -> map 
    styled_df = filtered_anomalies.style.map(highlight_risk, subset=['위험도'])
    st.dataframe(styled_df, use_container_width=True)

    def to_excel(df):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='이상치_리포트')
        return output.getvalue()

    st.download_button(
        label="📥 내부감사 엑셀 리포트 다운로드",
        data=to_excel(filtered_anomalies),
        file_name='SIMPAC_내부감사_리포트.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


# ==============================================================================
# [프로젝트 2] 제조원가 검증 및 결산 보조 대시보드
# ==============================================================================
def run_project2():
    st.title("🏭 SIMPAC 다사업부(BU) 제조원가 검증 및 결산 대시보드")
    st.markdown("""
    **[채용전환형 인턴 포트폴리오 - 프로젝트 2]**  
    각 사업부(프레스, 메탈, 산업기계 등)의 월별 제조원가 명세서를 분석하고, **표준원가 대비 실제원가 차이(Variance)를 검증**하여 월 결산(Closing)의 정확도와 속도를 높이는 자동화 대시보드입니다.
    """)

    @st.cache_data
    def generate_cost_data():
        np.random.seed(42)
        bu_list = ['프레스 BU', '메탈(합금철) BU', '산업기계 BU', 'ENG BU']
        
        cost_structure = {
            '직접재료비': ['열연강판/후판', '철스크랩', '페로실리콘(원료)', '부재료'],
            '직접노무비': ['생산직급여', '상여금', '퇴직급여'],
            '제조경비': ['전력비', '감가상각비', '외주가공비', '수선비', '소모품비']
        }
        
        data = []
        for month in range(1, 4):
            for bu in bu_list:
                for cost_type, details in cost_structure.items():
                    for detail in details:
                        base_standard_cost = np.random.randint(50, 500)
                        
                        if bu == '메탈(합금철) BU' and detail == '전력비':
                            base_standard_cost *= 5 
                        if bu == '프레스 BU' and detail in ['열연강판/후판', '외주가공비']:
                            base_standard_cost *= 3
                            
                        variance_rate = np.random.uniform(-0.15, 0.25)
                        actual_cost = base_standard_cost * (1 + variance_rate)
                        
                        data.append({
                            '결산월': f'2025-0{month}',
                            '사업부': bu,
                            '원가요소': cost_type,
                            '세부계정': detail,
                            '표준원가(백만원)': int(base_standard_cost),
                            '실제원가(백만원)': int(actual_cost)
                        })
                        
        df = pd.DataFrame(data)
        df['차이금액'] = df['실제원가(백만원)'] - df['표준원가(백만원)']
        df['차이율(%)'] = round((df['차이금액'] / df['표준원가(백만원)']) * 100, 1)
        
        outlier_idx = np.random.choice(df.index, 5, replace=False)
        df.loc[outlier_idx, '실제원가(백만원)'] = df.loc[outlier_idx, '표준원가(백만원)'] * 1.45
        df.loc[outlier_idx, '차이금액'] = df.loc[outlier_idx, '실제원가(백만원)'] - df.loc[outlier_idx, '표준원가(백만원)']
        df.loc[outlier_idx, '차이율(%)'] = round((df.loc[outlier_idx, '차이금액'] / df.loc[outlier_idx, '표준원가(백만원)']) * 100, 1)
        
        return df

    df = generate_cost_data()

    st.markdown("### 🗓️ 결산월 및 BU 필터")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        selected_month = st.selectbox("결산월 선택", options=sorted(df['결산월'].unique(), reverse=True))
    with col_f2:
        selected_bu = st.multiselect("[결산] 사업부 선택", options=df['사업부'].unique(), default=df['사업부'].unique())

    filtered_df = df[(df['결산월'] == selected_month) & (df['사업부'].isin(selected_bu))]

    total_standard = filtered_df['표준원가(백만원)'].sum()
    total_actual = filtered_df['실제원가(백만원)'].sum()
    total_variance = filtered_df['차이금액'].sum()
    variance_pct = (total_variance / total_standard) * 100 if total_standard > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 당기제품제조원가(실제)", f"{total_actual:,.0f} 백만원", delta=f"{variance_pct:.1f}% (대비 표준)", delta_color="inverse")
    with col2:
        st.metric("총 표준원가", f"{total_standard:,.0f} 백만원")
    with col3:
        st.metric("원가 차이(불리한 차이)", f"{total_variance:,.0f} 백만원")
    with col4:
        error_cnt = len(filtered_df[filtered_df['차이율(%)'] >= 20])
        st.metric("🚨 결산 검증 요망 건수", f"{error_cnt} 건")

    st.divider()

    tab1, tab2, tab3 = st.tabs(["📊 사업부별 원가 분석", "🔍 원가요소별 비중 (명세서)", "⚠️ 결산 이상치 검증(원가차이)"])

    with tab1:
        st.subheader("사업부별 실제원가 vs 표준원가 비교")
        bu_grouped = filtered_df.groupby('사업부')[['표준원가(백만원)', '실제원가(백만원)']].sum().reset_index()
        fig1 = go.Figure()
        fig1.add_trace(go.Bar(x=bu_grouped['사업부'], y=bu_grouped['표준원가(백만원)'], name='표준원가', marker_color='#a6cee3'))
        fig1.add_trace(go.Bar(x=bu_grouped['사업부'], y=bu_grouped['실제원가(백만원)'], name='실제원가', marker_color='#1f78b4'))
        fig1.update_layout(barmode='group', template='plotly_white')
        st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.subheader("당월 원가요소 구성비")
            cost_type_grouped = filtered_df.groupby('원가요소')['실제원가(백만원)'].sum().reset_index()
            fig2 = px.pie(cost_type_grouped, values='실제원가(백만원)', names='원가요소', hole=0.4, template='plotly_white', color_discrete_sequence=px.colors.qualitative.Set2)
            st.plotly_chart(fig2, use_container_width=True)
        with col_t2:
            st.subheader("제조경비 세부 항목 (Drill-down)")
            overhead_df = filtered_df[filtered_df['원가요소'] == '제조경비']
            fig3 = px.treemap(overhead_df, path=['사업부', '세부계정'], values='실제원가(백만원)', template='plotly_white')
            st.plotly_chart(fig3, use_container_width=True)

    with tab3:
        st.subheader("🚨 결산 전 필수 검증 대상 (원가 차이율 20% 이상 계정)")
        anomalies_df = filtered_df[filtered_df['차이율(%)'] >= 20].sort_values(by='차이율(%)', ascending=False)
        
        def highlight_variance(val):
            color = '#ffcccc' if val >= 30 else '#fff2cc' if val >= 20 else ''
            return f'background-color: {color}'
        
        # [수정 완료] applymap -> map 
        st.dataframe(anomalies_df.style.map(highlight_variance, subset=['차이율(%)']), use_container_width=True)

    st.divider()

    def convert_df_to_excel(df):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='원가명세서')
        return output.getvalue()

    st.download_button(
        label="📥 월별 제조원가명세서 다운로드 (ERP 전송용)",
        data=convert_df_to_excel(filtered_df),
        file_name=f"SIMPAC_제조원가결산_{selected_month}.xlsx",
        mime="application/vnd.ms-excel"
    )

# ==============================================================================
# 메인 화면 구성 및 사이드바 내비게이션
# ==============================================================================
st.sidebar.title("재무/회계 포트폴리오")
st.sidebar.markdown("지원자: **[구민준]**")
st.sidebar.divider()

# 프로젝트 선택 라디오 버튼
selected_project = st.sidebar.radio(
    "📊 분석 프로젝트 선택",
    ("1. 내부통제 및 이상치 탐지 (증빙 대사)", "2. 제조원가 검증 및 결산 보조")
)

st.sidebar.divider()
st.sidebar.info("본 대시보드는 SIMPAC의 비즈니스 구조를 모티브로 제작된 가상 데이터 기반 포트폴리오입니다.")

# 선택된 메뉴에 따라 함수 실행
if selected_project == "1. 내부통제 및 이상치 탐지 (증빙 대사)":
    run_project1()
elif selected_project == "2. 제조원가 검증 및 결산 보조":
    run_project2()
