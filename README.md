# Fyers Real-time Momentum Scanner (Streamlit)

This application provides a professional dashboard for tracking real-time stock momentum using the Fyers API.

## 🚀 Deployment Instructions

### Local Run
1. Install dependencies: `pip install -r requirements.txt`
2. Ensure `symbols.txt` and `access_token.txt` are in the project folder.
3. Run the app: `streamlit run app.py`

### GitHub & Streamlit Cloud Deployment
1. **Create a Private Repository** on GitHub and upload all files.
2. **Setup Streamlit Cloud**:
   - Go to [share.streamlit.io](https://share.streamlit.io).
   - Connect your GitHub repo.
3. **Secrets Management**:
   - Since GitHub should not have your API keys, use Streamlit's **Secrets** feature.
   - Go to App Settings -> Secrets and add your credentials if you decide to hide them from the code.

## 📁 File Structure
- `app.py`: Main dashboard code.
- `requirements.txt`: List of libraries for the cloud server.
- `symbols.txt`: Your watchlist.
- `access_token.txt`: Your current Fyers token.

## ⚠️ Important Note
The Fyers Access Token expires daily. You will need to update the `access_token.txt` file (or the Secret in Streamlit Cloud) every morning before the market opens.
