import yfinance as yf
import pandas as pd
import numpy as np
from ta.trend import SMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
import streamlit as st
from datetime import datetime, timedelta

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
    def get_data(self, ticker):
        try:
            # Pega dados mais longos para médias longas
            df = yf.download(ticker, period='2y', progress=False, auto_adjust=True)
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
        if df is None or not i: return 0, "N/A"
        score = 0
        curr = df['Close'].iloc[-1]
        
        # Tendência
        if 'SMA20' in i and curr > i['SMA20'].iloc[-1]: score += 10
        if 'SMA50' in i and curr > i['SMA50'].iloc[-1]: score += 15
        if 'SMA200' in i and curr > i['SMA200'].iloc[-1]: score += 20 # Peso maior para longo prazo
        
        # RSI
        rsi = i['RSI'].iloc[-1] if 'RSI' in i else 50
        if rsi < 30: score += 25 # Forte oportunidade
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
        """Calcula DY somando dividendos dos últimos 12 meses (Correção do erro 0%)"""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.dividends
            if hist.empty: return 0.0
            
            # Filtra últimos 12 meses
            start_date = (datetime.now() - timedelta(days=365)).replace(tzinfo=None)
            hist.index = hist.index.tz_localize(None)
            divs_12m = hist[hist.index >= start_date].sum()
            
            # Preço atual
            price = stock.history(period='1d')['Close'].iloc[-1]
            if price > 0:
                return (divs_12m / price) * 100
            return 0.0
        except:
            return 0.0

    def get_fundamentals(self, ticker, category):
        if category == 'Commodities': return None
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Tenta pegar DY pronto, se falhar, calcula manual
            dy = info.get('dividendYield', 0)
            if dy is None or dy == 0:
                dy = self.calculate_dy_manual(ticker)
            else:
                dy = dy * 100

            return {
                'P/L': info.get('trailingPE', 0),
                'P/VP': info.get('priceToBook', 0),
                'DY': dy,
                'ROE': (info.get('returnOnEquity', 0) or 0) * 100
            }
        except: return None

    def generate_fund_score(self, data, category):
        if not data: return 0, "N/A"
        score = 50
        
        # Lógica Específica para FIAGROS
        if "Fiagros" in category:
            # DY é o rei
            if data['DY'] > 13: score += 35 # Excelente pagador
            elif data['DY'] > 10: score += 20
            elif data['DY'] < 6: score -= 20
            
            # P/VP (Desconto vs Ágio)
            pvp = data.get('P/VP', 0)
            if pvp > 0:
                if pvp < 0.90: score += 25 # Desconto alto
                elif 0.90 <= pvp <= 1.05: score += 15 # Preço justo
                elif pvp > 1.20: score -= 15 # Caro
        else:
            # Lógica Ações
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
        """Gera texto explicativo em linguagem natural"""
        insight = []
        
        # Análise Técnica
        if t_score >= 70: insight.append("Tendência gráfica muito forte.")
        elif t_score <= 30: insight.append("Gráfico aponta forte correção.")
        else: insight.append("Movimento lateral no gráfico.")
        
        # Análise Fundamentalista
        if "Fiagros" in category:
            if dy > 11: insight.append(f"Excelente pagador de dividendos ({dy:.1f}% aa).")
            elif dy < 8: insight.append(f"Dividendos abaixo da média do setor ({dy:.1f}% aa).")
        else:
            if f_score >= 70: insight.append("Fundamentos robustos e baratos.")
            elif f_score <= 40: insight.append("Múltiplos esticados ou baixa rentabilidade.")
            
        return " ".join(insight)
