import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from agro_analytics import AgroDatabase, TechnicalEngine, FundamentalEngine

st.set_page_config(page_title="AgroMonitor Pro V4.3", page_icon="🚜", layout="wide")

st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #f0f2f6; border-radius: 4px 4px 0 0; }
    .stTabs [aria-selected="true"] { background-color: #2E7D32; color: white; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_system():
    return AgroDatabase(), TechnicalEngine(), FundamentalEngine()

db, tech_eng, fund_eng = load_system()

st.title("🚜 AgroMonitor Pro V4.3")
st.caption(f"Inteligência de Mercado: Ações • Fiagros • Commodities • BDRs | {pd.Timestamp.now().strftime('%d/%m/%Y')}")

st.sidebar.header("⚙️ Painel de Controle")
min_score = st.sidebar.slider("Score Técnico Mínimo", 0, 100, 30)
search_ticker = st.sidebar.text_input("Filtrar Ativo (ex: SLCE3)", "").upper()

if st.sidebar.button("🔄 Atualizar Dados", type="primary"):
    st.cache_data.clear()
    st.rerun()

assets_map = db.assets 

def render_tab(category_name, assets_dict):
    results = []
    
    for ticker, name in assets_dict.items():
        if search_ticker and search_ticker not in ticker: continue
        
        df = tech_eng.get_data(ticker)
        if df is not None:
            inds = tech_eng.calculate_signals(df)
            t_score, t_status = tech_eng.generate_tech_score(df, inds)
            
            if t_score >= min_score:
                f_data = fund_eng.get_fundamentals(ticker, category_name)
                f_score, f_status = fund_eng.generate_fund_score(f_data, category_name)
                
                price = df['Close'].iloc[-1]
                var_pct = ((price / df['Close'].iloc[-2]) - 1) * 100
                dy_val = f_data['DY'] if f_data else 0
                
                results.append({
                    "Ativo": ticker.replace('.SA', ''),
                    "Nome": name,
                    "Preço": price,
                    "Var (1d)": var_pct,
                    "Score Téc.": t_score,
                    "Status Téc.": t_status,
                    "Score Fund.": f_score,
                    "Status Fund.": f_status,
                    "DY%": dy_val,
                    "RSI": inds['RSI'].iloc[-1] if inds and 'RSI' in inds else 0
                })
    
    if results:
        df_res = pd.DataFrame(results).sort_values("Score Téc.", ascending=False)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Oportunidades", len(df_res))
        c2.metric("Melhor Score Téc.", f"{df_res['Score Téc.'].max()}")
        
        max_dy = df_res['DY%'].max()
        if max_dy > 0:
            c3.metric("Maior DY%", f"{max_dy:.1f}%")
        else:
            c3.metric("Maior Alta (1d)", f"{df_res['Var (1d)'].max():.2f}%")
        
        st.dataframe(
            df_res,
            column_config={
                "Score Téc.": st.column_config.ProgressColumn("Força Téc.", min_value=0, max_value=100, format="%d"),
                "Preço": st.column_config.NumberColumn("Preço", format="R$ %.2f"),
                "Var (1d)": st.column_config.NumberColumn("Var %", format="%.2f%%"),
                "DY%": st.column_config.NumberColumn("DY Anual", format="%.1f%%"),
                "RSI": st.column_config.NumberColumn("RSI", format="%.0f"),
            },
            hide_index=True,
            use_container_width=True
        )
        
        st.markdown("---")
        
        # --- GRÁFICO SELECIONÁVEL (COM CORREÇÃO DE ERRO) ---
        col_sel, col_empty = st.columns([1, 2])
        with col_sel:
            lista_ativos = df_res['Ativo'].tolist()
            ativo_selecionado = st.selectbox(f"📊 Ver gráfico de {category_name}:", lista_ativos)
        
        full_ticker = ativo_selecionado
        if category_name != 'Commodities' and ".SA" not in full_ticker:
             full_ticker += ".SA"
        elif category_name == 'Commodities':
             for k, v in assets_dict.items():
                 if ativo_selecionado in k:
                     full_ticker = k
                     break

        st.subheader(f"📈 Análise Técnica: {ativo_selecionado}")
        
        df_chart = tech_eng.get_data(full_ticker)
        
        if df_chart is not None:
            inds_chart = tech_eng.calculate_signals(df_chart)
            
            # --- PLOTAGEM SEGURA (EVITA KEYERROR) ---
            if inds_chart:
                fig = go.Figure()
                
                # Preço
                fig.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], 
                                           low=df_chart['Low'], close=df_chart['Close'], name='Preço'))
                
                # Médias (Só plota se existirem no dicionário)
                if 'SMA20' in inds_chart:
                    fig.add_trace(go.Scatter(x=df_chart.index, y=inds_chart['SMA20'], name='SMA 20', line=dict(color='orange', width=1.5)))
                if 'SMA50' in inds_chart:
                    fig.add_trace(go.Scatter(x=df_chart.index, y=inds_chart['SMA50'], name='SMA 50', line=dict(color='blue', width=1.5)))
                
                # Bandas de Bollinger (Causa comum de erro, agora protegida)
                if 'BB_H' in inds_chart and 'BB_L' in inds_chart:
                    fig.add_trace(go.Scatter(x=df_chart.index, y=inds_chart['BB_H'], name='BB High', 
                                           line=dict(color='gray', width=1, dash='dot'), showlegend=False))
                    fig.add_trace(go.Scatter(x=df_chart.index, y=inds_chart['BB_L'], name='BB Low', 
                                           line=dict(color='gray', width=1, dash='dot'), fill='tonexty', 
                                           fillcolor='rgba(200,200,200,0.1)', showlegend=False))
                
                fig.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_white",
                                margin=dict(l=20, r=20, t=30, b=20), legend=dict(orientation="h", y=1.05, x=0))
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Dados técnicos insuficientes para gerar indicadores deste ativo.")
        else:
            st.error("Não foi possível carregar o gráfico. Tente recarregar a página.")
            
    else:
        st.info(f"Nenhum ativo em '{category_name}' atende aos filtros atuais.")

tabs = st.tabs(["🌱 Fiagros (Renda)", "🇧🇷 Ações BR", "🌎 BDRs & ETFs", "🛢️ Commodities"])

with tabs[0]: render_tab("Fiagros (Renda)", assets_map['Fiagros (Renda)'])
with tabs[1]: render_tab("Ações BR", assets_map['Ações BR'])
with tabs[2]: render_tab("BDRs & ETFs", assets_map['BDRs & ETFs'])
with tabs[3]: render_tab("Commodities", assets_map['Commodities'])
