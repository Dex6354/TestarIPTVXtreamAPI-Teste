import streamlit as st
import re
import requests
from urllib.parse import quote, urlparse, parse_qs
from datetime import datetime
import urllib3

# Desabilitar avisos de segurança para certificados SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuração da Página
st.set_page_config(page_title="IPTV Checker Pro", layout="centered")

# Headers que simulam um aplicativo real para tentar pular o Erro 406
HEADERS = {
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 10; SM-G981B Build/QP1A.190711.020)",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive",
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
                netloc = p.netloc
                base_original = f"{p.scheme}://{netloc}"
                results.append({"base": base_original, "user": user, "pwd": pwd, "type": "Original"})
                
                # Rota alternativa removendo o "cdn." que causa erro 406
                if 'cdn.' in netloc:
                    alt_netloc = netloc.replace('cdn.', '')
                    base_alt = f"{p.scheme}://{alt_netloc}"
                    results.append({"base": base_alt, "user": user, "pwd": pwd, "type": "Sem CDN (Bypass)"})
        except:
            continue
    return results

def test_server(data):
    base, user, pwd = data["base"], data["user"], data["pwd"]
    api_url = f"{base}/player_api.php?username={quote(user)}&password={quote(pwd)}"
    
    try:
        response = requests.get(api_url, headers=HEADERS, verify=False, timeout=15)
        if response.status_code == 200:
            try:
                json_data = response.json()
                if "user_info" in json_data:
                    return {"success": True, "data": json_data, "code": 200}
            except:
                pass
        return {"success": False, "code": response.status_code}
    except Exception as e:
        return {"success": False, "code": str(e)}

# Interface Streamlit
st.title("🔌 IPTV Xtream Validator")

m3u_input = st.text_area("Cole sua URL M3U:", value="http://cdn.club8.ca/get.php?username=concmus03&password=3a3b3c3d&type=m3u_plus", height=100)

if st.button("🚀 Testar Conexão"):
    links = parse_urls(m3u_input)
    
    if not links:
        st.error("Nenhuma credencial encontrada.")
    else:
        for link in links:
            with st.spinner(f"Testando rota {link['type']}: {link['base']}..."):
                res = test_server(link)
                
                if res["success"]:
                    ui = res["data"]["user_info"]
                    st.success(f"✅ Conectado com sucesso via rota: {link['type']}")
                    with st.container(border=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"👤 **Usuário:** `{link['user']}`")
                            exp = ui.get("exp_date")
                            if exp and exp != "null":
                                dt = datetime.fromtimestamp(int(exp)).strftime('%d/%m/%Y')
                                st.write(f"📅 **Expira:** `{dt}`")
                            else:
                                st.write(f"📅 **Expira:** `Ilimitado`")
                        with col2:
                            st.write(f"👥 **Conexões:** `{ui.get('active_cons')}/{ui.get('max_connections')}`")
                            st.write(f"📡 **Status:** `{ui.get('status')}`")
                    st.balloons()
                    break 
                else:
                    st.warning(f"❌ Rota {link['type']} falhou. Erro: {res['code']}")

st.info("Nota: Se todas as rotas falharem com erro 406 no Streamlit, execute este código no seu computador local.")
