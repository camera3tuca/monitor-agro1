import yfinance as yf
import pandas as pd
import numpy as np
from ta.trend import SMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
import streamlit as st

# --- BANCO DE DADOS (BASEADO NO BLOG TORO + B3) ---
class AgroDatabase:
    def __init__(self):
        self.assets = {
            'Ações BR': {
                'SLCE3.SA': 'SLC Agrícola (Grãos)',
                'AGRO3.SA': 'BrasilAgro (Terras)',
                'SMTO3.SA': 'São Martinho (Açúcar)',
                'RAIZ4.SA': 'Raízen (Bioenergia)',
                'JALL3.SA': 'Jalles Machado (Açúcar)',
                'SOJA3.SA': 'Boa Safra (Sementes)',
                'TTEN3.SA': '3Tentos (Varejo)',
                'AGXY3.SA': 'AgroGalaxy (Insumos)',
                'BEEF3.SA': 'Minerva (Boi)',
                'MRFG3.SA': 'Marfrig (Boi)',
                'JBSS3.SA': 'JBS (Global)',
                'BRFS3.SA': 'BRF (Aves/Suínos)',
                'CAML3.SA': 'Camil (Alimentos)',
                'MDIA3.SA': 'M. Dias Branco (Massas)',
                'JOPA3.SA': 'Josapar (Arroz)',
                'SUZB3.SA': 'Suzano (Celulose)',
                'KLBN11.SA': 'Klabin (Papel)',
                'KEPL3.SA': 'Kepler Weber (Silos)'
            },
            'Fiagros (Renda)': {
                'SNAG11.SA': 'Suno Agro',
                'KNCA11.SA': 'Kinea Agro',
                'VGIA11.SA': 'Valora CRA',
                'BBGO11.SA': 'BB Crédito',
                'FGAA11.SA': 'FG Agro',
                'RZAG11.SA': 'Riza Agro',
                'XPCA11.SA': 'XP Crédito',
                'AGRX11.SA': 'Exes Araguaia'
            },
            'BDRs & ETFs': {
                'DE': 'Deere & Co (Maquinário)',
                'AGCO': 'AGCO Corp (Maquinário)',
                'ADM': 'Archer Daniels (Trading)',
                'BG': 'Bunge (Trading)',
                'MOS': 'Mosaic (Fertilizantes)',
                'NTR': 'Nutrien (Fertilizantes)',
                'CTVA': 'Corteva (Sementes)',
                'CF': 'CF Industries (Nitrogênio)',
                'BVEG39.SA': 'iShares Global Agric.',
                'RZTR11.SA': 'Investo Teckma (Terras)'
            },
            'Commodities': {
                'ZC=F': 'Milho (Chicago)',
                'ZS=F': 'Soja (Chicago)',
                'KC=F': 'Café (Nova York)',
                'LE=F': 'Boi Gordo (Futuro)',
                'SB=F': 'Açúcar (Bruto)'
            }
        }

    def get_all_tickers(self):
        tickers = []
        for cat in self.assets.values():
            tickers.extend(list(cat.keys()))
        return tickers

    def get_info(self, ticker):
        for cat, items in self.assets.items():
            if ticker in items:
                return items[ticker], cat
        return ticker, "Outros"

# --- ENGINE TÉCNICA (COM FIX DE ERRO 404) ---
class TechnicalEngine:
    def get_data(self, ticker):
        try:
            # Baixa dados com tratamento de erro silencioso
            df = yf.download(ticker, period='1y', progress=False, auto_adjust=True)
            
            if df.empty or len(df) < 50: return None
            
            # Tratamento para novas versões do YFinance (MultiIndex)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except: return None

    def calculate_signals(self, df):
        if df is None: return None
        close = df['Close']
        i = {}
        i['SMA20'] = SMAIndicator(close, 20).sma_indicator()
        i['SMA50'] = SMAIndicator(close, 50).sma_indicator()
        i['SMA200'] = SMAIndicator(close, 200).sma_indicator()
        i['RSI'] = RSIIndicator(close, 14).rsi()
        macd = MACD(close)
        i['MACD'] = macd.macd()
        i['MACD_S'] = macd.macd_signal()
        return i

    def generate_tech_score(self, df, i):
        if df is None or i is None: return 0, "N/A"
        score = 0
        curr = df['Close'].iloc[-1]
        
        # Tendência
        if curr > i['SMA20'].iloc[-1]: score += 10
        if curr > i['SMA50'].iloc[-1]: score += 15
        if curr > i['SMA200'].iloc[-1]: score += 15
        
        # RSI
        rsi = i['RSI'].iloc[-1]
        if rsi < 30: score += 20      # Oportunidade
        elif 30 <= rsi <= 60: score += 10 # Zona Neutra
        elif rsi > 70: score -= 10    # Risco
        
        # MACD
        if i['MACD'].iloc[-1] > i['MACD_S'].iloc[-1]: score += 30
        
        final = min(100, max(0, score))
        if final >= 75: status = "🟢 FORTE"
        elif final >= 60: status = "🟢 COMPRA"
        elif final >= 40: status = "⚪ NEUTRO"
        else: status = "🔴 VENDA"
        return final, status

# --- ENGINE FUNDAMENTALISTA (LÓGICA HÍBRIDA) ---
class FundamentalEngine:
    def get_fundamentals(self, ticker, category):
        # Commodities não têm fundamentos de balanço
        if category == 'Commodities': return None
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            data = {
                'P/L': info.get('trailingPE', 0),
                'P/VP': info.get('priceToBook', 0),
                'DY': (info.get('dividendYield', 0) or 0) * 100,
                'ROE': (info.get('returnOnEquity', 0) or 0) * 100
            }
            return data
        except: return None

    def generate_fund_score(self, data, category):
        if not data: return 0, "N/A"
        
        score = 50
        
        # Lógica para FIAGROS (Foco em Renda e P/VP)
        if "Fiagros" in category:
            # P/VP ideal próximo de 1.0
            if 0.90 <= data['P/VP'] <= 1.10: score += 30
            elif data['P/VP'] < 0.90: score += 40 # Desconto
            elif data['P/VP'] > 1.20: score -= 20 # Caro
            
            # Dividend Yield é rei
            if data['DY'] > 12: score += 20
            elif data['DY'] > 10: score += 10
            
        else: # Ações e BDRs (Crescimento + Valor)
            if 0 < data['P/L'] <= 15: score += 15
            if 0 < data['P/VP'] <= 2.0: score += 15
            if data['ROE'] >= 10: score += 10
            if data['DY'] >= 6: score += 10
            
        final = min(100, max(0, score))
        if final >= 70: status = "💎 EXCELENTE"
        elif final >= 50: status = "✅ SÓLIDO"
        else: status = "⚠️ ATENÇÃO"
        return final, status
