import streamlit as st
import re
import requests
from urllib.parse import quote, urlparse, parse_qs
from datetime import datetime
import urllib3

# Desabilitar avisos de segurança
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Xtream API - Ultra Bypass", layout="centered")

# Simulação de Headers de um Smart TV Samsung (muito aceito por servidores IPTV)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (SmartHub; SMART-TV; Samsung; LGNetCast.TV-2013; LG Browser) AppleWebKit/537.1 (KHTML, like Gecko) Safari/537.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
    "Cache-Control": "max-age=0",
    "Upgrade-Insecure-Requests": "1"
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
                # Pegar apenas o domínio e porta
                base_url = f"{p.scheme}://{p.netloc}"
                results.append({"base": base_url, "user": user, "pwd": pwd})
        except: continue
    return results

def test_server(data):
    base, user, pwd = data["base"], data["user"], data["pwd"]
    
    # Tentativa 1: player_api.php (Padrão)
    # Tentativa 2: xmltv.php (Geralmente tem menos bloqueio que player_api)
    endpoints = [
        f"{base}/player_api.php?username={user}&password={pwd}",
        f"{base}/xmltv.php?username={user}&password={pwd}"
    ]
    
    result = {"success": False, "msg": "Bloqueio 406", "data": None}
    
    for url in endpoints:
        try:
            # Usamos uma sessão para simular persistência
            session = requests.Session()
            response = session.get(url, headers=HEADERS, verify=False, timeout=15)
            
            if response.status_code == 200:
                try:
                    json_data = response.json()
                    if "user_info" in json_data:
                        if json_data["user_info"].get("auth") == 1:
                            result["success"] = True
                            result["data"] = json_data
                            return result
                        else:
                            result["msg"] = "Credenciais incorretas"
                            return result
                except:
                    # Se não for JSON, pode ser o XML do xmltv.php
                    if "<?xml" in response.text:
                        result["success"] = True
                        result["msg"] = "Logado via XML (API JSON bloqueada)"
                        return result
            elif response.status_code == 406:
                continue # Tenta o próximo endpoint
        except:
            continue

    return result

# --- Interface ---
st.title("🔌 Xtream API Bypass")
st.warning("O servidor cdn.club8.ca possui firewall rigoroso. Tentando métodos alternativos...")

url_input = st.text_area("Cole seu link:", "http://cdn.club8.ca/get.php?username=concmus03&password=3a3b3c3d&type=m3u_plus")

if st.button("🚀 Forçar Entrada"):
    links = parse_urls(url_input)
    
    if not links:
        st.error("URL inválida.")
    else:
        for link in links:
            with st.status(f"Analisando {link['base']}...") as status:
                res = test_server(link)
                
                if res["success"]:
                    status.update(label="✅ Sucesso!", state="complete")
                    if res["data"]:
                        ui = res["data"]["user_info"]
                        st.success(f"Logado como: {link['user']}")
                        st.json(ui)
                    else:
                        st.warning(res["msg"])
                else:
                    status.update(label=f"❌ {res['msg']}", state="error")
                    st.error(f"O servidor ainda recusa a conexão (Erro 406).")
                    
                    st.info("""
                    **Por que isso acontece?**
                    O domínio `cdn.club8.ca` usa uma proteção que bloqueia o IP do Streamlit. 
                    **Teste o seguinte:**
                    1. Troque `cdn.club8.ca` por `club8.ca` (sem o cdn).
                    2. Tente rodar o script localmente em seu computador, pois o seu IP residencial raramente é bloqueado por erro 406.
                    """)

st.divider()
st.caption("Nota: Se você estiver usando o Streamlit Cloud, o IP deles pode estar na blacklist global desse servidor de IPTV.")
