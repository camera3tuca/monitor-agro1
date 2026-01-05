import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from agro_analytics import AgroDatabase, TechnicalEngine, FundamentalEngine
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="AgroMonitor Premium V6.4", page_icon="🌾", layout="wide")

# --- CSS EXECUTIVO ---
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border-left: 5px solid #2E7D32;
        padding: 15px;
        border-radius: 5px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    div[data-testid="stDataFrame"] { background-color: white; border-radius: 10px; padding: 10px; }
    .stTabs [aria-selected="true"] { background-color: #2E7D32 !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

# --- CARREGAMENTO ---
@st.cache_resource
def load_system():
    return AgroDatabase(), TechnicalEngine(), FundamentalEngine()

db, tech_eng, fund_eng = load_system()

# --- SIDEBAR ---
with st.sidebar:
    st.title("🚜 AgroMonitor V6.4")
    min_score = st.slider("Score Técnico Mínimo", 0, 100, 30)
    search_ticker = st.text_input("🔍 Buscar Ativo", "").upper()
    st.markdown("---")
    if st.button("🔄 Atualizar Análise", type="primary"):
        st.cache_data.clear()
        st.rerun()

# --- HEADER ---
col1, col2 = st.columns([3, 1])
with col1:
    st.title("Monitor Executivo do Agronegócio")
with col2:
    st.markdown(f"*{pd.Timestamp.now().strftime('%d/%m/%Y')}*")

# --- FUNÇÃO DE GAUGE ---
def create_gauge(value, title):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        title = {'text': title, 'font': {'size': 14}},
        gauge = {
            'axis': {'range': [0, 100]},
            'bar': {'color': "#2E7D32" if value >= 60 else "#f9a825" if value >= 40 else "#c62828"},
            'steps': [{'range': [0, 40], 'color': "#ffebee"}, {'range': [40, 70], 'color': "#fff3e0"}, {'range': [70, 100], 'color': "#e8f5e9"}],
        }
    ))
    fig.update_layout(height=150, margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor="rgba(0,0,0,0)")
    return fig

# --- RENDERIZAÇÃO ---
def render_premium_tab(category_name, assets_dict):
    results = []
    
    # 1. VARREDURA (COM SLEEP)
    # Barra de progresso para dar feedback visual
    progress_bar = st.progress(0)
    total_assets = len(assets_dict)
    
    for i, (ticker, name) in enumerate(assets_dict.items()):
        if search_ticker and search_ticker not in ticker: continue
        
        # ATUALIZA BARRA E PAUSA
        progress_bar.progress((i + 1) / total_assets)
        time.sleep(0.5) # Pausa estratégica
        
        df = tech_eng.get_data(ticker)
        if df is not None:
            inds = tech_eng.calculate_signals(df)
            if not inds: continue
            
            t_score, t_status = tech_eng.generate_tech_score(df, inds)
            
            if t_score >= min_score:
                f_data = fund_eng.get_fundamentals(ticker, category_name)
                f_score, f_status = fund_eng.generate_fund_score(f_data, category_name)
                
                price = df['Close'].iloc[-1]
                var_pct = ((price / df['Close'].iloc[-2]) - 1) * 100
                dy_val = f_data['DY'] if f_data else 0
                
                insight_text = fund_eng.generate_insight(t_score, f_score, dy_val, category_name)
                
                results.append({
                    "Ticker": ticker.replace('.SA', ''),
                    "Nome": name,
                    "Preço": price,
                    "Var%": var_pct,
                    "Score Téc.": t_score,
                    "Score Fund.": f_score,
                    "DY%": dy_val,
                    "Insight": insight_text,
                    "Status": t_status
                })
    
    progress_bar.empty()
    
    # 2. DASHBOARD
    if results:
        df_res = pd.DataFrame(results).sort_values("Score Téc.", ascending=False)
        top_asset = df_res.iloc[0]
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Oportunidades", len(df_res))
        k2.metric("Melhor Ativo", top_asset['Ticker'], delta=f"{top_asset['Score Téc.']} pts")
        
        if "Fiagros" in category_name:
            avg_dy = df_res['DY%'].mean()
            k3.metric("Média de Dividendos", f"{avg_dy:.2f}%", delta="Anual")
        else:
            avg_var = df_res['Var%'].mean()
            k3.metric("Variação do Setor", f"{avg_var:.2f}%")
            
        k4.metric("Sentimento Geral", "Otimista" if df_res['Score Téc.'].mean() > 50 else "Cauteloso")
        
        st.divider()
        
        col_table, col_detail = st.columns([2, 1])
        
        with col_table:
            st.subheader("📋 Classificação de Mercado")
            st.dataframe(
                df_res,
                column_config={
                    "Score Téc.": st.column_config.ProgressColumn("Técnico", min_value=0, max_value=100, format="%d"),
                    "Score Fund.": st.column_config.ProgressColumn("Fundam.", min_value=0, max_value=100, format="%d"),
                    "Preço": st.column_config.NumberColumn("Preço", format="R$ %.2f"),
                    "Var%": st.column_config.NumberColumn("Var (1d)", format="%.2f%%"),
                    "DY%": st.column_config.NumberColumn("DY (12m)", format="%.1f%%"),
                    "Insight": st.column_config.TextColumn("Análise IA", width="medium"),
                },
                hide_index=True,
                use_container_width=True
            )
        
        with col_detail:
            st.markdown(f"### 🏆 Destaque: {top_asset['Ticker']}")
            st.info(top_asset['Insight'])
            
            g1, g2 = st.columns(2)
            # --- FIX CRUCIAL: CHAVES ÚNICAS PARA OS GRÁFICOS ---
            # O parâmetro key=f"..." evita o erro StreamlitDuplicateElementId
            with g1: 
                st.plotly_chart(
                    create_gauge(top_asset['Score Téc.'], "Técnico"), 
                    use_container_width=True, 
                    key=f"gauge_tec_{category_name}_{top_asset['Ticker']}"
                )
            with g2: 
                st.plotly_chart(
                    create_gauge(top_asset['Score Fund.'], "Fundamentos"), 
                    use_container_width=True, 
                    key=f"gauge_fund_{category_name}_{top_asset['Ticker']}"
                )
            
            if top_asset['DY%'] > 0:
                st.success(f"💰 **Dividend Yield:** {top_asset['DY%']:.2f}% ao ano")
        
        st.markdown("---")
        st.subheader(f"📈 Análise Gráfica: {top_asset['Ticker']}")
        
        full_ticker = top_asset['Ticker']
        if category_name != 'Commodities' and ".SA" not in full_ticker: full_ticker += ".SA"
        elif category_name == 'Commodities': 
             for k, v in assets_dict.items():
                 if top_asset['Ticker'] in k: full_ticker = k; break
        
        df_chart = tech_eng.get_data(full_ticker)
        if df_chart is not None:
            inds = tech_eng.calculate_signals(df_chart)
            
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            
            fig.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'],
                                       low=df_chart['Low'], close=df_chart['Close'], name='Preço'), row=1, col=1)
            if 'SMA20' in inds:
                fig.add_trace(go.Scatter(x=df_chart.index, y=inds['SMA20'], name='Média 20', line=dict(color='orange')), row=1, col=1)
            if 'SMA200' in inds:
                fig.add_trace(go.Scatter(x=df_chart.index, y=inds['SMA200'], name='Média 200', line=dict(color='blue')), row=1, col=1)
            
            if 'MACD' in inds:
                fig.add_trace(go.Scatter(x=df_chart.index, y=inds['MACD'], name='MACD', line=dict(color='purple')), row=2, col=1)
                fig.add_trace(go.Bar(x=df_chart.index, y=inds['MACD']-inds['MACD_S'], name='Hist', marker_color='gray'), row=2, col=1)
            
            fig.update_layout(height=500, template="plotly_white", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
            
            # Key única para o gráfico principal também
            st.plotly_chart(fig, use_container_width=True, key=f"chart_main_{category_name}_{top_asset['Ticker']}")

    else:
        st.warning(f"Nenhum ativo encontrado em '{category_name}' com os filtros atuais.")

# --- ABAS ---
tabs = st.tabs(["🌱 Fiagros (Renda)", "🇧🇷 Ações (Crescimento)", "🌎 Global (BDRs)", "🛢️ Commodities"])

assets_map = db.assets
with tabs[0]: render_premium_tab("Fiagros", assets_map['Fiagros (Renda Mensal)'])
with tabs[1]: render_premium_tab("Ações", assets_map['Ações (Crescimento)'])
with tabs[2]: render_premium_tab("Global", assets_map['Global (BDRs/ETFs)'])
with tabs[3]: render_premium_tab("Commodities", assets_map['Commodities'])
