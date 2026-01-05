import yfinance as yf
import pandas as pd
import numpy as np
from ta.trend import SMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
import streamlit as st
from datetime import datetime, timedelta
import time

# --- CONFIGURAÇÃO ---
BRAPI_TOKEN = st.secrets.get("BRAPI_TOKEN", "iExnKM1xcbQcYL3cNPhPQ3")

class AgroDatabase:
    def __init__(self):
        self.assets = {
            'Fiagros (Renda Mensal)': {
                'SNAG11.SA': 'Suno Agro', 'KNCA11.SA': 'Kinea Agro', 'VGIA11.SA': 'Valora CRA',
                'BBGO11.SA': 'BB Crédito', 'FGAA11.SA': 'FG Agro', 'RZAG11.SA': 'Riza Agro',
                'XPCA11.SA': 'XP Crédito', 'AGRX11.SA': 'Exes Araguaia', 'CPTR11.SA': 'Capitania',
                'RURA11.SA': 'Itaú Rural', 'OIAG11.SA': 'Ourinvest'
            },
            'Ações (Crescimento)': {
                'SLCE3.SA': 'SLC Agrícola', 'AGRO3.SA': 'BrasilAgro', 'SMTO3.SA': 'São Martinho',
                'RAIZ4.SA': 'Raízen', 'SOJA3.SA': 'Boa Safra', 'TTEN3.SA': '3Tentos',
                'AGXY3.SA': 'AgroGalaxy', 'BEEF3.SA': 'Minerva', 'MRFG3.SA': 'Marfrig',
                'JBSS3.SA': 'JBS', 'BRFS3.SA': 'BRF', 'CAML3.SA': 'Camil', 'MDIA3.SA': 'M. Dias Branco',
                'SUZB3.SA': 'Suzano', 'KLBN11.SA': 'Klabin', 'KEPL3.SA': 'Kepler Weber'
            },
            'Global (BDRs/ETFs)': {
                'DE': 'Deere & Co', 'AGCO': 'AGCO Corp', 'ADM': 'Archer Daniels',
                'BG': 'Bunge', 'MOS': 'Mosaic', 'NTR': 'Nutrien', 'CTVA': 'Corteva',
                'CF': 'CF Industries', 'BVEG39.SA': 'iShares Global', 'RZTR11.SA': 'Investo Teckma'
            },
            'Commodities': {
                'ZC=F': 'Milho (Chicago)', 'ZS=F': 'Soja (Chicago)', 'KC=F': 'Café (NY)',
                'LE=F': 'Boi Gordo', 'SB=F': 'Açúcar'
            }
        }

    def get_info(self, ticker):
        for cat, items in self.assets.items():
            if ticker in items: return items[ticker], cat
        return ticker, "Outros"

class TechnicalEngine:
    # CACHE DE 4 HORAS: Evita chamar o Yahoo toda hora e ser bloqueado
    @st.cache_data(ttl=14400, show_spinner=False)
    def get_data(_self, ticker):
        time.sleep(0.3) # Pausa respeitosa entre requisições
        for _ in range(2):
            try:
                df = yf.download(ticker, period='2y', progress=False, auto_adjust=True)
                if not df.empty and len(df) > 50:
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    return df
                time.sleep(1)
            except: 
                time.sleep(1)
        return None

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
        if df is None or not i: return 0, "N/A"
        score = 0
        curr = df['Close'].iloc[-1]
        
        # Tendência
        if 'SMA20' in i and curr > i['SMA20'].iloc[-1]: score += 10
        if 'SMA50' in i and curr > i['SMA50'].iloc[-1]: score += 15
        if 'SMA200' in i and curr > i['SMA200'].iloc[-1]: score += 20 
        
        # RSI
        rsi = i['RSI'].iloc[-1] if 'RSI' in i else 50
        if rsi < 30: score += 25
        elif 30 <= rsi <= 60: score += 10
        elif rsi > 70: score -= 10
        
        # MACD
        if 'MACD' in i and i['MACD'].iloc[-1] > i['MACD_S'].iloc[-1]: score += 20
        
        final = min(100, max(0, score))
        if final >= 75: status = "🟢 COMPRA FORTE"
        elif final >= 60: status = "🟢 COMPRA"
        elif final >= 40: status = "⚪ NEUTRO"
        else: status = "🔴 VENDA"
        return final, status

class FundamentalEngine:
    def calculate_dy_manual(self, ticker):
        try:
            stock = yf.Ticker(ticker)
            hist = stock.dividends
            if hist.empty: return 0.0
            start_date = (datetime.now() - timedelta(days=365)).replace(tzinfo=None)
            hist.index = hist.index.tz_localize(None)
            divs_12m = hist[hist.index >= start_date].sum()
            
            hist_price = stock.history(period='5d')
            if not hist_price.empty:
                price = hist_price['Close'].iloc[-1]
                if price > 0: return (divs_12m / price) * 100
            return 0.0
        except: return 0.0

    # CACHE DE 4 HORAS: Vital para fundamentos
    @st.cache_data(ttl=14400, show_spinner=False)
    def get_fundamentals(_self, ticker, category):
        if category == 'Commodities': return None
        
        # Tenta pegar DY pronto, se falhar, calcula manual
        dy_manual = _self.calculate_dy_manual(ticker)
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Se a API falhar, usamos o DY calculado manualmente e zeramos o resto
            if not info or len(info) < 2:
                return {'P/L': 0, 'P/VP': 0, 'DY': dy_manual, 'ROE': 0}

            dy_api = info.get('dividendYield', 0)
            dy_final = (dy_api * 100) if dy_api and dy_api > 0 else dy_manual

            return {
                'P/L': info.get('trailingPE', 0),
                'P/VP': info.get('priceToBook', 0),
                'DY': dy_final,
                'ROE': (info.get('returnOnEquity', 0) or 0) * 100
            }
        except:
            # Fallback total
            return {'P/L': 0, 'P/VP': 0, 'DY': dy_manual, 'ROE': 0}

    def generate_fund_score(self, data, category):
        if not data: return 0, "N/A"
        score = 50
        
        if "Fiagros" in category:
            if data['DY'] > 13: score += 35
            elif data['DY'] > 10: score += 20
            elif data['DY'] < 6: score -= 20
            
            pvp = data.get('P/VP', 0)
            if pvp > 0:
                if pvp < 0.90: score += 25
                elif 0.90 <= pvp <= 1.05: score += 15
                elif pvp > 1.20: score -= 15
        else:
            if 0 < data['P/L'] <= 12: score += 20
            if 0 < data['P/VP'] <= 2.0: score += 15
            if data['ROE'] >= 15: score += 15
            if data['DY'] >= 6: score += 10
            
        final = min(100, max(0, score))
        if final >= 70: status = "💎 EXCELENTE"
        elif final >= 50: status = "✅ SÓLIDO"
        else: status = "⚠️ ATENÇÃO"
        return final, status

    def generate_insight(self, t_score, f_score, dy, category):
        insight = []
        if t_score >= 70: insight.append("Tendência gráfica muito forte.")
        elif t_score <= 30: insight.append("Gráfico aponta forte correção.")
        else: insight.append("Movimento lateral no gráfico.")
        
        if "Fiagros" in category:
            if dy > 11: insight.append(f"Excelente pagador ({dy:.1f}% aa).")
            elif dy < 8: insight.append(f"Dividendos baixos ({dy:.1f}% aa).")
        else:
            if f_score >= 70: insight.append("Fundamentos robustos.")
            elif f_score <= 40: insight.append("Múltiplos esticados.")
            
        return " ".join(insight)
