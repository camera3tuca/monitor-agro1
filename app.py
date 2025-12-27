import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from agro_analytics import AgroDatabase, TechnicalEngine, FundamentalEngine

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="AgroMonitor Pro V5.0", page_icon="🚜", layout="wide")

# --- CSS PERSONALIZADO ---
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #f0f2f6; border-radius: 4px 4px 0 0; }
    .stTabs [aria-selected="true"] { background-color: #2E7D32; color: white; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; }
</style>
""", unsafe_allow_html=True)

# --- CARREGAMENTO DO SISTEMA ---
@st.cache_resource
def load_system():
    return AgroDatabase(), TechnicalEngine(), FundamentalEngine()

db, tech_eng, fund_eng = load_system()

# --- HEADER ---
st.title("🚜 AgroMonitor Pro V5.0")
st.caption(f"Inteligência de Mercado: Ações • Fiagros • Commodities • BDRs | {pd.Timestamp.now().strftime('%d/%m/%Y')}")

# --- SIDEBAR ---
st.sidebar.header("⚙️ Painel de Controle")
min_score = st.sidebar.slider("Score Técnico Mínimo", 0, 100, 30)
search_ticker = st.sidebar.text_input("Filtrar Ativo (ex: SLCE3)", "").upper()

if st.sidebar.button("🔄 Atualizar Dados", type="primary"):
    st.cache_data.clear()
    st.rerun()

assets_map = db.assets 

# --- FUNÇÃO DE RENDERIZAÇÃO ---
def render_tab(category_name, assets_dict):
    results = []
    
    # 1. VARREDURA
    for ticker, name in assets_dict.items():
        if search_ticker and search_ticker not in ticker: continue
        
        df = tech_eng.get_data(ticker)
        if df is not None:
            inds = tech_eng.calculate_signals(df)
            # Verifica se os indicadores foram calculados corretamente
            if not inds: continue 
            
            t_score, t_status = tech_eng.generate_tech_score(df, inds)
            
            if t_score >= min_score:
                f_data = fund_eng.get_fundamentals(ticker, category_name)
                f_score, f_status = fund_eng.generate_fund_score(f_data, category_name)
                
                price = df['Close'].iloc[-1]
                var_pct = ((price / df['Close'].iloc[-2]) - 1) * 100
                dy_val = f_data['DY'] if f_data else 0
                
                # Check seguro para RSI
                rsi_val = inds['RSI'].iloc[-1] if 'RSI' in inds else 0
                
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
                    "RSI": rsi_val
                })
    
    # 2. EXIBIÇÃO
    if results:
        df_res = pd.DataFrame(results).sort_values("Score Téc.", ascending=False)
        
        # Métricas
        c1, c2, c3 = st.columns(3)
        c1.metric("Oportunidades", len(df_res))
        c2.metric("Melhor Score Téc.", f"{df_res['Score Téc.'].max()}")
        max_dy = df_res['DY%'].max()
        if max_dy > 0:
            c3.metric("Maior DY%", f"{max_dy:.1f}%")
        else:
            c3.metric("Maior Alta (1d)", f"{df_res['Var (1d)'].max():.2f}%")
        
        # Tabela
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
        
        # --- GRÁFICO PROFISSIONAL (SUBPLOTS IGUAL AO COLAB) ---
        col_sel, _ = st.columns([1, 2])
        with col_sel:
            lista_ativos = df_res['Ativo'].tolist()
            ativo_selecionado = st.selectbox(f"📊 Análise Técnica Avançada ({category_name}):", lista_ativos)
        
        # Reconstrói ticker
        full_ticker = ativo_selecionado
        if category_name != 'Commodities' and ".SA" not in full_ticker:
             full_ticker += ".SA"
        elif category_name == 'Commodities':
             for k, v in assets_dict.items():
                 if ativo_selecionado in k:
                     full_ticker = k
                     break

        df_chart = tech_eng.get_data(full_ticker)
        
        if df_chart is not None:
            inds_chart = tech_eng.calculate_signals(df_chart)
            
            if inds_chart:
                # Cria 4 painéis (Preço, Volume, RSI, MACD)
                fig = make_subplots(
                    rows=4, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.03,
                    row_heights=[0.5, 0.15, 0.15, 0.2],
                    subplot_titles=(f'{ativo_selecionado} - Preço', 'Volume', 'RSI', 'MACD')
                )
                
                # 1. Candlestick + Médias
                fig.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], 
                                           low=df_chart['Low'], close=df_chart['Close'], name='Preço'), row=1, col=1)
                
                if 'SMA20' in inds_chart:
                    fig.add_trace(go.Scatter(x=df_chart.index, y=inds_chart['SMA20'], name='SMA 20', line=dict(color='orange', width=1)), row=1, col=1)
                if 'SMA50' in inds_chart:
                    fig.add_trace(go.Scatter(x=df_chart.index, y=inds_chart['SMA50'], name='SMA 50', line=dict(color='blue', width=1)), row=1, col=1)
                if 'SMA200' in inds_chart:
                    fig.add_trace(go.Scatter(x=df_chart.index, y=inds_chart['SMA200'], name='SMA 200', line=dict(color='red', width=1.5)), row=1, col=1)
                
                # Bandas de Bollinger
                if 'BB_H' in inds_chart and 'BB_L' in inds_chart:
                    fig.add_trace(go.Scatter(x=df_chart.index, y=inds_chart['BB_H'], name='BB High', 
                                           line=dict(color='gray', width=1, dash='dot'), showlegend=False), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df_chart.index, y=inds_chart['BB_L'], name='BB Low', 
                                           line=dict(color='gray', width=1, dash='dot'), fill='tonexty', 
                                           fillcolor='rgba(200,200,200,0.1)', showlegend=False), row=1, col=1)

                # 2. Volume
                colors = ['red' if row['Close'] < row['Open'] else 'green' for _, row in df_chart.iterrows()]
                fig.add_trace(go.Bar(x=df_chart.index, y=df_chart['Volume'], name='Volume', marker_color=colors), row=2, col=1)
                
                # 3. RSI
                if 'RSI' in inds_chart:
                    fig.add_trace(go.Scatter(x=df_chart.index, y=inds_chart['RSI'], name='RSI', line=dict(color='purple')), row=3, col=1)
                    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
                    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
                
                # 4. MACD
                if 'MACD' in inds_chart and 'MACD_S' in inds_chart and 'MACD' in inds_chart: # MACD Hist not always available directly from ta library in simple call, calculating manually if needed or using library output
                     # A biblioteca TA retorna MACD (linha), MACD_S (sinal). O Histograma é a diferença.
                     macd_hist = inds_chart['MACD'] - inds_chart['MACD_S']
                     
                     fig.add_trace(go.Scatter(x=df_chart.index, y=inds_chart['MACD'], name='MACD', line=dict(color='blue')), row=4, col=1)
                     fig.add_trace(go.Scatter(x=df_chart.index, y=inds_chart['MACD_S'], name='Sinal', line=dict(color='orange')), row=4, col=1)
                     fig.add_trace(go.Bar(x=df_chart.index, y=macd_hist, name='Hist.', marker_color='gray'), row=4, col=1)

                fig.update_layout(height=900, xaxis_rangeslider_visible=False, template="plotly_white", showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Dados técnicos insuficientes.")
        else:
            st.error("Erro ao carregar dados do gráfico.")
    else:
        st.info(f"Nenhum ativo encontrado em '{category_name}'.")

# --- ABAS ---
tabs = st.tabs(["🌱 Fiagros (Renda)", "🇧🇷 Ações BR", "🌎 BDRs & ETFs", "🛢️ Commodities"])

with tabs[0]: render_tab("Fiagros (Renda)", assets_map['Fiagros (Renda)'])
with tabs[1]: render_tab("Ações BR", assets_map['Ações BR'])
with tabs[2]: render_tab("BDRs & ETFs", assets_map['BDRs & ETFs'])
with tabs[3]: render_tab("Commodities", assets_map['Commodities'])
