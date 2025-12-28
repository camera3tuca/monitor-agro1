import yfinance as yf
import pandas as pd
import numpy as np
from ta.trend import SMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
import streamlit as st

# --- CONFIGURAÇÃO ---
BRAPI_TOKEN = st.secrets.get("BRAPI_TOKEN", "iExnKM1xcbQcYL3cNPhPQ3")

class AgroDatabase:
    def __init__(self):
        self.assets = {
            'Ações BR': {
                'SLCE3.SA': 'SLC Agrícola (Grãos)', 'AGRO3.SA': 'BrasilAgro (Terras)', 'SMTO3.SA': 'São Martinho (Açúcar)',
                'RAIZ4.SA': 'Raízen (Bioenergia)', 'JALL3.SA': 'Jalles Machado (Açúcar)', 'SOJA3.SA': 'Boa Safra (Sementes)',
                'TTEN3.SA': '3Tentos (Varejo)', 'AGXY3.SA': 'AgroGalaxy (Insumos)', 'BEEF3.SA': 'Minerva (Boi)',
                'MRFG3.SA': 'Marfrig (Boi)', 'JBSS3.SA': 'JBS (Global)', 'BRFS3.SA': 'BRF (Aves/Suínos)',
                'CAML3.SA': 'Camil (Alimentos)', 'MDIA3.SA': 'M. Dias Branco (Massas)', 'JOPA3.SA': 'Josapar (Arroz)',
                'SUZB3.SA': 'Suzano (Celulose)', 'KLBN11.SA': 'Klabin (Papel)', 'KEPL3.SA': 'Kepler Weber (Silos)'
            },
            'Fiagros (Renda)': {
                'SNAG11.SA': 'Suno Agro', 'KNCA11.SA': 'Kinea Agro', 'VGIA11.SA': 'Valora CRA',
                'BBGO11.SA': 'BB Crédito', 'FGAA11.SA': 'FG Agro', 'RZAG11.SA': 'Riza Agro',
                'XPCA11.SA': 'XP Crédito', 'AGRX11.SA': 'Exes Araguaia', 'CPTR11.SA': 'Capitania Agro'
            },
            'BDRs & ETFs': {
                'DE': 'Deere & Co (Maquinário)', 'AGCO': 'AGCO Corp (Maquinário)', 'ADM': 'Archer Daniels (Trading)',
                'BG': 'Bunge (Trading)', 'MOS': 'Mosaic (Fertilizantes)', 'NTR': 'Nutrien (Fertilizantes)',
                'CTVA': 'Corteva (Sementes)', 'CF': 'CF Industries (Nitrogênio)', 'BVEG39.SA': 'iShares Global Agric.',
                'RZTR11.SA': 'Investo Teckma (Terras)'
            },
            'Commodities': {
                'ZC=F': 'Milho (Chicago)', 'ZS=F': 'Soja (Chicago)', 'KC=F': 'Café (Nova York)',
                'LE=F': 'Boi Gordo (Futuro)', 'SB=F': 'Açúcar (Bruto)'
            }
        }

    def get_info(self, ticker):
        for cat, items in self.assets.items():
            if ticker in items: return items[ticker], cat
        return ticker, "Outros"

class TechnicalEngine:
    def get_data(self, ticker):
        try:
            df = yf.download(ticker, period='1y', progress=False, auto_adjust=True)
            if df.empty or len(df) < 50: return None
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except: return None

    def calculate_signals(self, df):
        if df is None: return None
        close = df['Close']
        i = {}
        try:
            i['SMA20'] = SMAIndicator(close, 20).sma_indicator()
            i['SMA50'] = SMAIndicator(close, 50).sma_indicator()
            i['SMA200'] = SMAIndicator(close, 200).sma_indicator()
            i['RSI'] = RSIIndicator(close, 14).rsi()
            macd = MACD(close)
            i['MACD'] = macd.macd()
            i['MACD_S'] = macd.macd_signal()
            bb = BollingerBands(close, 20, 2)
            i['BB_H'] = bb.bollinger_hband()
            i['BB_L'] = bb.bollinger_lband()
        except: return None
        return i

    def generate_tech_score(self, df, i):
        if df is None or i is None: return 0, "N/A"
        score = 0
        curr = df['Close'].iloc[-1]
        
        # Lógica de Pontuação
        if 'SMA20' in i and curr > i['SMA20'].iloc[-1]: score += 10
        if 'SMA50' in i and curr > i['SMA50'].iloc[-1]: score += 15
        if 'SMA200' in i and curr > i['SMA200'].iloc[-1]: score += 15
        
        rsi = i['RSI'].iloc[-1] if 'RSI' in i else 50
        if rsi < 30: score += 20
        elif 30 <= rsi <= 60: score += 10
        elif rsi > 70: score -= 10
        
        if 'MACD' in i and i['MACD'].iloc[-1] > i['MACD_S'].iloc[-1]: score += 30
        
        final = min(100, max(0, score))
        if final >= 75: status = "🟢 FORTE"
        elif final >= 60: status = "🟢 COMPRA"
        elif final >= 40: status = "⚪ NEUTRO"
        else: status = "🔴 VENDA"
        return final, status

    def generate_insight(self, df, i, ticker):
        """Gera um texto explicativo automático (Feature Premium)"""
        if not i: return "Dados insuficientes."
        
        curr = df['Close'].iloc[-1]
        rsi = i['RSI'].iloc[-1]
        sma200 = i['SMA200'].iloc[-1]
        
        trend = "Alta" if curr > sma200 else "Baixa"
        momento = "Sobrevendido (Oportunidade)" if rsi < 30 else "Sobrecomprado (Cuidado)" if rsi > 70 else "Neutro"
        
        return f"O ativo {ticker} está em tendência de **{trend}** no longo prazo (vs SMA200). O momento atual é **{momento}** com RSI em {rsi:.0f}."

class FundamentalEngine:
    def get_fundamentals(self, ticker, category):
        if category == 'Commodities': return None
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return {
                'P/L': info.get('trailingPE', 0),
                'P/VP': info.get('priceToBook', 0),
                'DY': (info.get('dividendYield', 0) or 0) * 100,
                'ROE': (info.get('returnOnEquity', 0) or 0) * 100
            }
        except: return None

    def generate_fund_score(self, data, category):
        if not data: return 0, "N/A"
        score = 50
        
        if "Fiagros" in category:
            if 0.90 <= data['P/VP'] <= 1.10: score += 30
            elif data['P/VP'] < 0.90: score += 40
            else: score -= 20
            if data['DY'] > 12: score += 20
        else:
            if 0 < data['P/L'] <= 15: score += 15
            if 0 < data['P/VP'] <= 2.0: score += 15
            if data['ROE'] >= 10: score += 10
            if data['DY'] >= 6: score += 10
            
        final = min(100, max(0, score))
        if final >= 70: status = "💎 EXCELENTE"
        elif final >= 50: status = "✅ SÓLIDO"
        else: status = "⚠️ ATENÇÃO"
        return final, status
