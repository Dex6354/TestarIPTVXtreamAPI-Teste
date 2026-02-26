import streamlit as st
import re
import requests
from urllib.parse import quote, urlparse, parse_qs
from datetime import datetime
import urllib3

# Desabilitar avisos de segurança
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Xtream API Fix 406", layout="centered")

# HEADERS REFORÇADOS PARA EVITAR ERRO 406
# Simulando exatamente um app mobile para enganar o firewall
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "X-Requested-With": "com.nst.iptvsmartersptvbox"
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
                clean_path = p.path.lower().replace('get.php', '').replace('player_api.php', '')
                if clean_path.endswith('/'): clean_path = clean_path[:-1]
                base_url = f"{p.scheme}://{p.netloc}{clean_path}"
                results.append({"base": base_url, "user": user, "pwd": pwd})
        except: continue
    return results

def test_server(data):
    base, user, pwd = data["base"], data["user"], data["pwd"]
    # Forçamos o uso do player_api.php
    api_url = f"{base}/player_api.php?username={quote(user)}&password={quote(pwd)}"
    
    result = {"success": False, "msg": "Offline", "data": None}
    
    try:
        # Criamos uma sessão para manter cookies se necessário
        session = requests.Session()
        response = session.get(api_url, headers=HEADERS, verify=False, timeout=20)
        
        if response.status_code == 200:
            try:
                json_data = response.json()
                if "user_info" in json_data and json_data.get("user_info", {}).get("auth") == 1:
                    result["success"] = True
                    result["data"] = json_data
                else:
                    result["msg"] = "Credenciais Inválidas ou Conta Vencida"
            except:
                result["msg"] = "O servidor respondeu, mas não é um formato Xtream válido."
        else:
            result["msg"] = f"Erro HTTP {response.status_code} (Bloqueio de Segurança)"
            
    except Exception as e:
        result["msg"] = f"Erro de Conexão: {str(e)}"
        
    return result

# --- INTERFACE ---
st.title("🔌 Corretor Xtream (Anti-Block 406)")

url_input = st.text_area("Cole seu link M3U aqui:", placeholder="http://cdn.club8.ca/get.php?username=...")

if st.button("🚀 Forçar Conexão"):
    links = parse_urls(url_input)
    
    if not links:
        st.error("Nenhuma URL detectada.")
    else:
        for link in links:
            with st.spinner(f"Tentando burlar firewall de {link['base']}..."):
                res = test_server(link)
                
                if res["success"]:
                    ui = res["data"]["user_info"]
                    with st.container(border=True):
                        st.balloons()
                        st.success("✅ Conexão Estabelecida!")
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"👤 **Usuário:** `{link['user']}`")
                            exp = ui.get("exp_date")
                            date = datetime.fromtimestamp(int(exp)).strftime('%d/%m/%Y') if (exp and int(exp) > 0) else "Ilimitado"
                            st.write(f"📅 **Expira:** `{date}`")
                        with c2:
                            st.write(f"👥 **Conexões:** `{ui.get('active_cons')}/{ui.get('max_connections')}`")
                            st.write(f"📡 **Status:** `{ui.get('status')}`")
                else:
                    st.error(f"Falha: {res['msg']}")
                    st.info("O servidor cdn.club8.ca é rígido. Se o erro 406 persistir, o servidor exige que a conexão venha de um IP de dispositivo físico, não de um servidor de hospedagem.")

st.divider()
st.caption("Nota: Se o erro 406 continuar, tente trocar 'http' por 'https' manualmente na URL colada.")
