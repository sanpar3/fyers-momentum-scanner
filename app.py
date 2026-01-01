import streamlit as st
import pandas as pd
import datetime
import time
import threading
import os
import json
from fyers_apiv3.FyersWebsocket.data_ws import FyersDataSocket

# --- ⚙️ CONFIGURATION & STATE ---
SYMBOLS_FILE = "symbols.txt"
TOKEN_FILE = "access_token.txt"
CLIENT_ID = "XH11906"

# We use a mutable container (dictionary) that can be passed to the thread.
# This avoids using st.session_state inside the thread (which causes KeyErrors).
if 'shared_data' not in st.session_state:
    st.session_state.shared_data = {
        "positive": [],
        "negative": [],
        "history": {},
        "intervals": set(),
        "connected": False,
        "symbols_count": 0,
        "lookback": 60,   # Default 60s
        "percent": 1.0,   # Default 1.0%
        "last_update": datetime.datetime.now()
    }

# Thread lock for safety
data_lock = threading.Lock()

# --- 🛠️ HELPER FUNCTIONS ---
def load_watchlist():
    formatted_symbols = []
    if os.path.exists(SYMBOLS_FILE):
        with open(SYMBOLS_FILE, "r") as f:
            for line in f:
                s = line.strip().upper()
                if not s: continue
                if not (s.startswith("NSE:") or s.startswith("BSE:") or s.startswith("MCX:")):
                    s = f"NSE:{s}"
                if not s.endswith("-EQ") and "-INDEX" not in s: 
                    s = f"{s}-EQ"
                formatted_symbols.append(s)
    return list(set(formatted_symbols))

# --- 🔥 THREAD-SAFE CALLBACK ---
# This function runs in the background thread.
# It uses 'data' (the shared dictionary) passed explicitly, 
# NOT st.session_state.
def on_message(message, data):
    # Read config from the shared dict (updated by UI)
    lookback = data["lookback"]
    percent = data["percent"]
    
    if isinstance(message, dict) and "symbol" in message:
        sym = message["symbol"]
        ltp = message.get("ltp")
        if ltp is None: return
        
        now = datetime.datetime.now()
        
        with data_lock:
            # Update history
            if sym not in data["history"]: data["history"][sym] = []
            data["history"][sym].append((now, ltp))
            
            # Trim old data
            cutoff = now - datetime.timedelta(seconds=lookback)
            data["history"][sym] = [t for t in data["history"][sym] if t[0] >= cutoff]
            
            # Momentum Calc logic
            if len(data["history"][sym]) > 2:
                start_dt, start_price = data["history"][sym][0]
                elapsed = (now - start_dt).total_seconds()
                
                # Check if enough time passed (80% of window)
                if elapsed >= (lookback * 0.8):
                    pct_chg = ((ltp - start_price) / start_price) * 100
                    interval_key = f"{sym}_{now.strftime('%H:%M')}"
                    
                    if interval_key not in data["intervals"]:
                        alert = {
                            "Time": now.strftime('%H:%M:%S'), 
                            "Symbol": sym, 
                            "Move%": f"{pct_chg:.2f}%", 
                            "LTP": ltp
                        }
                        
                        if pct_chg >= percent:
                            data["positive"].insert(0, alert)
                            data["intervals"].add(interval_key)
                        elif pct_chg <= -percent:
                            data["negative"].insert(0, alert)
                            data["intervals"].add(interval_key)
            
            # Keep lists manageable
            data["positive"] = data["positive"][:50]
            data["negative"] = data["negative"][:50]
            data["last_update"] = now

# --- 🧵 BACKGROUND THREAD ---
def start_websocket(shared_data):
    symbols = load_watchlist()
    
    # Safely update shared_data
    with data_lock:
        shared_data["symbols_count"] = len(symbols)
    
    if not os.path.exists(TOKEN_FILE):
        print("❌ access_token.txt not found!") # Prints to server console
        return

    with open(TOKEN_FILE, "r") as f:
        access_token = f.read().strip()

    # Pass 'shared_data' to the callback using lambda
    fyers = FyersDataSocket(
        access_token=f"{CLIENT_ID}:{access_token}",
        litemode=False, reconnect=True,
        on_connect=lambda: fyers.subscribe(symbols=symbols, data_type="SymbolUpdate"),
        on_message=lambda msg: on_message(msg, shared_data),
        on_error=lambda msg: print(f"WS Error: {msg}"),
        on_close=lambda msg: print(f"WS Closed: {msg}")
    )
    fyers.connect()

# --- 🖥️ STREAMLIT UI ---
st.set_page_config(page_title="Fyers Momentum Pro", layout="wide")

st.title("📡 Fyers Real-time Momentum Scanner")

# Sidebar Configuration
st.sidebar.header("Settings")
# Update the shared dict directly so the thread sees changes
st.session_state.shared_data["lookback"] = st.sidebar.slider(
    "Lookback (Seconds)", 30, 900, st.session_state.shared_data["lookback"], 30
)
st.session_state.shared_data["percent"] = st.sidebar.number_input(
    "Momentum % Threshold", 0.1, 5.0, st.session_state.shared_data["percent"], 0.1
)

# Start Button
if st.sidebar.button("🚀 Start Scanner"):
    if not st.session_state.shared_data["connected"]:
        # Only start if not already running
        # Pass the container explicitly to the thread
        thread = threading.Thread(
            target=start_websocket, 
            args=(st.session_state.shared_data,), 
            daemon=True
        )
        thread.start()
        st.session_state.shared_data["connected"] = True
        st.sidebar.success("Scanner Started!")
    else:
        st.sidebar.warning("Scanner is already running.")

# Status Bar
status_cols = st.columns(4)
status_cols[0].metric("Status", "🟢 Running" if st.session_state.shared_data["connected"] else "🔴 Stopped")
status_cols[1].metric("Tracked Symbols", st.session_state.shared_data["symbols_count"])
status_cols[2].metric("Last Alert", st.session_state.shared_data["last_update"].strftime('%H:%M:%S'))

# --- 📊 DUAL TABLE LAYOUT ---
st.write("---")
col1, col2 = st.columns(2)

with col1:
    st.subheader(f"🚀 Positive Spikes (>{st.session_state.shared_data['percent']}%)")
    if st.session_state.shared_data["positive"]:
        st.dataframe(pd.DataFrame(st.session_state.shared_data["positive"]), use_container_width=True)
    else:
        st.info("Scanning for bullish moves...")

with col2:
    st.subheader(f"📉 Negative Drops (<-{st.session_state.shared_data['percent']}%)")
    if st.session_state.shared_data["negative"]:
        st.dataframe(pd.DataFrame(st.session_state.shared_data["negative"]), use_container_width=True)
    else:
        st.info("Scanning for bearish moves...")

# Auto-refresh UI every 1 second
time.sleep(1)
st.rerun()
