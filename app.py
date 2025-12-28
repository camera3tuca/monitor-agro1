import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from agro_analytics import AgroDatabase, TechnicalEngine, FundamentalEngine

# --- CONFIGURAÇÃO PREMIUM ---
st.set_page_config(page_title="AgroMonitor Premium", page_icon="🌾", layout="wide")

# --- CSS PROFISSIONAL ---
st.markdown("""
<style>
    /* Cards de Métricas */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    /* Abas */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #f8f9fa;
        border-radius: 5px;
        font-weight: 600;
        border: 1px solid #ddd;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1b5e20 !important;
        color: white !important;
        border: none;
    }
    /* Título */
    h1 { color: #1b5e20; }
    /* Dataframe Header */
    thead tr th:first-child { display:none }
    tbody th { display:none }
</style>
""", unsafe_allow_html=True)

# --- CARREGAMENTO ---
@st.cache_resource
def load_system():
    return AgroDatabase(), TechnicalEngine(), FundamentalEngine()

db, tech_eng, fund_eng = load_system()

# --- SIDEBAR PREMIUM ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/tractor.png", width=80)
    st.title("AgroMonitor Pro")
    st.markdown("---")
    
    st.header("🔍 Filtros de Radar")
    min_score = st.slider("Qualidade Técnica Mínima", 0, 100, 40, help="Filtra ativos com base na análise técnica (Tendência + Momentum).")
    search_ticker = st.text_input("Buscar Ativo Específico", "", placeholder="Ex: SLCE3").upper()
    
    st.markdown("---")
    if st.button("🚀 Executar Scanner", type="primary"):
        st.cache_data.clear()
        st.rerun()
        
    st.info("💡 **Dica Premium:** Use a aba 'Fiagros' para buscar renda passiva mensal.")

# --- HEADER PRINCIPAL ---
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.title("Monitor de Inteligência do Agro")
    st.markdown(f"**Relatório Executivo** | Data: {pd.Timestamp.now().strftime('%d/%m/%Y')}")

# --- FUNÇÃO DE RENDERIZAÇÃO PREMIUM ---
def render_premium_tab(category_name, assets_dict):
    results = []
    
    # 1. PROCESSAMENTO DE DADOS
    for ticker, name in assets_dict.items():
        if search_ticker and search_ticker not in ticker: continue
        
        df = tech_eng.get_data(ticker)
        if df is not None:
            inds = tech_eng.calculate_signals(df)
            if not inds: continue
            
            t_score, t_status = tech_eng.generate_tech_score(df, inds)
            
            if t_score >= min_score:
                f_data = fund_eng.get_fundamentals(ticker, category_name)
                f_score, f_status = fund_eng.generate_fund_score(f_data, category_name)
                insight = tech_eng.generate_insight(df, inds, ticker)
                
                price = df['Close'].iloc[-1]
                var_pct = ((price / df['Close'].iloc[-2]) - 1) * 100
                dy_val = f_data['DY'] if f_data else 0
                
                results.append({
                    "Ticker": ticker.replace('.SA', ''),
                    "Empresa": name,
                    "Preço": price,
                    "Var%": var_pct,
                    "Score Téc.": t_score,
                    "Status Téc.": t_status,
                    "Score Fund.": f_score,
                    "Status Fund.": f_status,
                    "DY%": dy_val,
                    "Insight": insight,
                    "RSI": inds['RSI'].iloc[-1] if 'RSI' in inds else 50
                })
    
    # 2. EXIBIÇÃO
    if results:
        df_res = pd.DataFrame(results).sort_values("Score Téc.", ascending=False)
        top_asset = df_res.iloc[0] # O Líder
        
        # --- CARDS DE KPI (VISUAL PREMIUM) ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Oportunidades", len(df_res), delta="Ativos Rastreados")
        c2.metric("Líder do Ranking", top_asset['Ticker'], delta=f"{top_asset['Score Téc.']} pts")
        
        # Métrica Condicional (DY ou Alta)
        if category_name == 'Fiagros (Renda)':
            best_dy = df_res.sort_values("DY%", ascending=False).iloc[0]
            c3.metric("Maior Pagador (DY)", f"{best_dy['DY%']:.1f}%", delta=best_dy['Ticker'])
        else:
            best_var = df_res.sort_values("Var%", ascending=False).iloc[0]
            c3.metric("Maior Alta (24h)", f"{best_var['Var%']:.2f}%", delta=best_var['Ticker'])
            
        c4.metric("Sentimento Médio", f"{df_res['Score Téc.'].mean():.0f}/100")
        
        st.markdown("### 📋 Tabela de Classificação")
        
        # --- TABELA ESTILIZADA ---
        st.dataframe(
            df_res,
            column_config={
                "Score Téc.": st.column_config.ProgressColumn("Força Téc.", min_value=0, max_value=100, format="%d"),
                "Preço": st.column_config.NumberColumn("Cotação", format="R$ %.2f"),
                "Var%": st.column_config.NumberColumn("Var (1d)", format="%.2f%%"),
                "DY%": st.column_config.NumberColumn("DY Anual", format="%.1f%%"),
                "Insight": st.column_config.TextColumn("Resumo IA", width="large"),
            },
            hide_index=True,
            use_container_width=True
        )
        
        st.markdown("---")
        
        # --- DEEP DIVE: GRÁFICO DO LÍDER (SEM ERROS) ---
        st.markdown(f"## 🏆 Análise Profunda: **{top_asset['Ticker']}**")
        
        col_chart, col_info = st.columns([2, 1])
        
        # Coluna da Direita: Card de Detalhes
        with col_info:
            st.info(f"**Diagnóstico:** {top_asset['Insight']}")
            st.success(f"**Fundamentos:** {top_asset['Status Fund.']} (Score: {top_asset['Score Fund.']})")
            if top_asset['DY%'] > 0:
                st.metric("Dividend Yield", f"{top_asset['DY%']:.2f}%")
            
            with st.expander("📚 O que significam os indicadores?"):
                st.markdown("""
                * **SMA20/50:** Médias Móveis. Preço acima delas indica alta.
                * **RSI:** <30 (Sobrevendido/Barato), >70 (Caro).
                * **Bollinger:** Preço batendo na banda inferior pode indicar repique.
                """)

        # Coluna da Esquerda: Gráfico Plotly Pro
        with col_chart:
            # Reconstrói Ticker
            full_ticker = top_asset['Ticker']
            if category_name != 'Commodities' and ".SA" not in full_ticker: full_ticker += ".SA"
            elif category_name == 'Commodities': 
                 for k, v in assets_dict.items():
                     if top_asset['Ticker'] in k: full_ticker = k; break
            
            df_chart = tech_eng.get_data(full_ticker)
            if df_chart is not None:
                inds_c = tech_eng.calculate_signals(df_chart)
                if inds_c:
                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                      vertical_spacing=0.05, row_heights=[0.7, 0.3])
                    
                    # Candlestick
                    fig.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'],
                                               low=df_chart['Low'], close=df_chart['Close'], name='Preço'), row=1, col=1)
                    
                    # Médias
                    colors = {'SMA20': '#ff9800', 'SMA50': '#2196f3', 'SMA200': '#f44336'}
                    for m in ['SMA20', 'SMA50', 'SMA200']:
                        if m in inds_c:
                            fig.add_trace(go.Scatter(x=df_chart.index, y=inds_c[m], name=m, 
                                                   line=dict(color=colors[m], width=1)), row=1, col=1)
                    
                    # Bollinger
                    if 'BB_H' in inds_c:
                        fig.add_trace(go.Scatter(x=df_chart.index, y=inds_c['BB_H'], name='BB', 
                                               line=dict(color='gray', width=0), showlegend=False), row=1, col=1)
                        fig.add_trace(go.Scatter(x=df_chart.index, y=inds_c['BB_L'], name='BB', 
                                               line=dict(color='gray', width=0), fill='tonexty', 
                                               fillcolor='rgba(200,200,200,0.1)', showlegend=False), row=1, col=1)
                    
                    # RSI
                    if 'RSI' in inds_c:
                        fig.add_trace(go.Scatter(x=df_chart.index, y=inds_c['RSI'], name='RSI', 
                                               line=dict(color='#9c27b0')), row=2, col=1)
                        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
                        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
                    
                    fig.update_layout(height=600, template="plotly_white", margin=dict(t=30, b=20, l=20, r=20),
                                    xaxis_rangeslider_visible=False, legend=dict(orientation="h", y=1.02, x=0))
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Dados técnicos insuficientes para o gráfico.")

    else:
        st.warning(f"Nenhum ativo encontrado em '{category_name}' com os filtros atuais.")

# --- RENDERIZAÇÃO DAS ABAS ---
tabs = st.tabs(["🌱 Fiagros (Renda)", "🇧🇷 Ações BR", "🌎 BDRs & ETFs", "🛢️ Commodities"])

assets_map = db.assets
with tabs[0]: render_premium_tab("Fiagros (Renda)", assets_map['Fiagros (Renda)'])
with tabs[1]: render_premium_tab("Ações BR", assets_map['Ações BR'])
with tabs[2]: render_premium_tab("BDRs & ETFs", assets_map['BDRs & ETFs'])
with tabs[3]: render_premium_tab("Commodities", assets_map['Commodities'])
