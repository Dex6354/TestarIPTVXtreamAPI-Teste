import streamlit as st
import re
import requests
from urllib.parse import quote, urlparse, parse_qs
from datetime import datetime
import urllib3

# Limpeza de avisos
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Xtream API Fix", layout="centered")

# Headers Ultra-Realistas
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Origin": "http://cdn.club8.ca",
    "Referer": "http://cdn.club8.ca/"
}

def parse_urls(message):
    pattern = r"(https?://[^\s\"']+\?[^\s\"']+)"
    found_urls = re.findall(pattern, message)
    results = []
    for url in found_urls:
        try:
            p = urlparse(url)
            params = parse_qs(p.query)
            user = params.get('username', [None])[0]
            pwd = params.get('password', [None])[0]
            if user and pwd:
                base_url = f"{p.scheme}://{p.netloc}"
                results.append({"base": base_url, "user": user, "pwd": pwd})
        except: continue
    return results

def test_with_retry(base, user, pwd):
    """
    Tenta conexão normal. Se der 406, avisa o usuário sobre a necessidade de Proxy local.
    """
    api_url = f"{base}/player_api.php?username={quote(user)}&password={quote(pwd)}"
    
    try:
        # Tentativa 1: GET padrão com Session
        session = requests.Session()
        resp = session.get(api_url, headers=HEADERS, verify=False, timeout=15)
        
        if resp.status_code == 200:
            return {"success": True, "data": resp.json()}
        return {"success": False, "code": resp.status_code}
    except Exception as e:
        return {"success": False, "code": "Timeout/Rede"}

# Interface
st.title("🔌 Xtream API - Diagnóstico Final")

st.markdown("""
> **Aviso de Diagnóstico:** Se o erro **406** persistir aqui, significa que o firewall do servidor **CDN Club8** baniu o IP do Streamlit. 
""")

link_input = st.text_area("URL M3U:", "http://cdn.club8.ca/get.php?username=concmus03&password=3a3b3c3d&type=m3u_plus")

if st.button("🚀 Executar Diagnóstico"):
    links = parse_urls(link_input)
    
    if not links:
        st.error("URL Inválida.")
    else:
        for link in links:
            with st.spinner(f"Conectando a {link['base']}..."):
                res = test_with_retry(link['base'], link['user'], link['pwd'])
                
                if res["success"]:
                    ui = res["data"]["user_info"]
                    st.success("✅ CONECTADO!")
                    st.json(ui)
                elif res["code"] == 406:
                    st.error("❌ ERRO 406: Bloqueio de Provedor Cloud.")
                    st.info("""
                    **Como resolver agora:**
                    O servidor bloqueou o IP do site. Você precisa rodar este código **no seu computador**.
                    1. Salve o código num arquivo `app.py`.
                    2. No terminal do seu PC digite: `pip install streamlit requests`
                    3. Depois digite: `streamlit run app.py`
                    No seu computador (IP Residencial), o erro 406 não vai existir.
                    """)
                else:
                    st.error(f"Falha na conexão. Código: {res['code']}")
