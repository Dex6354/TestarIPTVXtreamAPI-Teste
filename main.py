import streamlit as st
import re
import requests
from urllib.parse import quote, urlparse, parse_qs
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import unicodedata
import urllib3

# Desabilitar avisos de segurança
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Xtream API Fix", layout="centered")

# HEADERS SIMULANDO SMARTERS PRO (Evita bloqueio de servidor)
HEADERS = {
    "User-Agent": "IPTVSmartersPlayer",
    "Accept": "*/*",
    "Connection": "keep-alive"
}

def normalize_text(text):
    if not isinstance(text, str): return ""
    return unicodedata.normalize('NFKD', text.lower()).encode('ascii', 'ignore').decode('utf-8')

def parse_urls(message):
    # Regex para capturar URLs que contenham username e password
    pattern = r"(https?://[^\s\"']+\?[^\s\"']+)"
    found_urls = re.findall(pattern, message)
    
    parsed_results = []
    unique_ids = set()

    for url in found_urls:
        try:
            parsed_url = urlparse(url)
            params = parse_qs(parsed_url.query)
            
            user = params.get('username', [None])[0]
            pwd = params.get('password', [None])[0]
            
            if user and pwd:
                # Extrai a base sem o arquivo (get.php ou player_api.php)
                base_path = parsed_url.path
                clean_path = base_path.replace('get.php', '').replace('player_api.php', '')
                if clean_path.endswith('/'): clean_path = clean_path[:-1]
                
                # Monta a base correta: http://dominio.com:porta
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{clean_path}"
                display_base = f"{parsed_url.scheme}://{parsed_url.hostname}"
                
                identifier = (base_url, user, pwd)
                if identifier not in unique_ids:
                    unique_ids.add(identifier)
                    parsed_results.append({
                        "base": base_url,
                        "display_base": display_base,
                        "username": user,
                        "password": pwd
                    })
        except: continue
    return parsed_results

def get_xtream_info(url_data, search_name=None):
    base, user, pwd = url_data["base"], url_data["username"], url_data["password"]
    
    # Montagem da URL de API
    api_url = f"{base}/player_api.php?username={quote(user)}&password={quote(pwd)}"
    
    res = {
        "is_json": False, "exp_date": "Falha no login",
        "active_cons": "N/A", "max_connections": "N/A", "has_adult_content": False,
        "is_accepted_domain": False, "live_count": 0, "vod_count": 0, "series_count": 0,
        "search_matches": {"Canais": [], "Filmes": [], "Séries": {}}
    }

    try:
        # Request principal com timeout maior
        response = requests.get(api_url, headers=HEADERS, verify=False, timeout=20)
        
        # Se o servidor retornar 200 OK mas não for JSON, ele pode estar bloqueando o User-Agent
        data_json = response.json()

        # Xtream Codes retorna "user_info" em caso de sucesso
        if "user_info" in data_json:
            u_info = data_json.get("user_info", {})
            
            # Se auth for 0, as credenciais estão erradas ou expiradas
            if u_info.get("auth") == 0:
                res["exp_date"] = "Credenciais Inválidas"
                return url_data, res

            res["is_json"] = True
            
            # Tratamento de expiração
            exp = u_info.get("exp_date")
            if exp and str(exp).isdigit():
                ts = int(exp)
                if ts == 0: res["exp_date"] = "Ilimitado"
                elif ts > 2147483647: res["exp_date"] = "Vitalício"
                else: res["exp_date"] = datetime.fromtimestamp(ts).strftime('%d/%m/%Y')
            
            res["active_cons"] = u_info.get("active_cons", "0")
            res["max_connections"] = u_info.get("max_connections", "0")
            
            # Verificação de domínios aceitos
            valid_tlds = ('.ca', '.io', '.cc', '.me', '.in', '.top', '.space')
            res["is_accepted_domain"] = any(url_data["display_base"].lower().endswith(tld) for tld in valid_tlds)

            # Contagem de conteúdos (Opcional para velocidade)
            actions = {"live": "get_live_streams", "vod": "get_vod_streams", "series": "get_series"}
            for key, act in actions.items():
                try:
                    r = requests.get(f"{api_url}&action={act}", headers=HEADERS, verify=False, timeout=15)
                    items = r.json()
                    if isinstance(items, list):
                        res[f"{key}_count"] = len(items)
                except: pass
    except Exception as e:
        res["exp_date"] = f"Erro: Offline"
        
    return url_data, res

# --- Interface Streamlit ---
st.title("🔌 Corretor Xtream API")

m3u_input = st.text_area("Cole a URL completa aqui:", height=100)
search_query = st.text_input("🔍 Buscar canal/filme (opcional):")

if st.button("🚀 Testar"):
    parsed = parse_urls(m3u_input)
    if not parsed:
        st.warning("Formato de URL não reconhecido. Certifique-se que tem 'username=' e 'password='.")
    else:
        for item in parsed:
            with st.spinner(f"Conectando a {item['display_base']}..."):
                orig, info = get_xtream_info(item, search_query)
                
                with st.container(border=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**Servidor:** `{orig['display_base']}`")
                        st.markdown(f"**Status:** {'✅ Logado' if info['is_json'] else '❌ Erro'}")
                        color = "green" if info['is_json'] else "red"
                        st.markdown(f"**Expiração:** :{color}[{info['exp_date']}]")
                    with c2:
                        st.write(f"📺 Canais: `{info['live_count']}`")
                        st.write(f"👥 Conexões: `{info['active_cons']}/{info['max_connections']}`")
                        st.write(f"🌐 Domínio OK: {'✅' if info['is_accepted_domain'] else '❌'}")
