import streamlit as st
import re
import requests
from urllib.parse import quote, urlparse, parse_qs
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import unicodedata
import urllib3

# Desabilitar avisos de segurança para certificados SSL inválidos
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuração da página do Streamlit
st.set_page_config(page_title="Testar Xtream API", layout="centered")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Connection": "keep-alive"
}

# Estilos CSS
st.markdown("""
    <style>
        .block-container { padding-top: 2.5rem; }
        .stCodeBlock, code { white-space: pre-wrap !important; word-break: break-all !important; }
        a { word-break: break-all !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <h5 style='margin-bottom: 0.1rem;'>🔌 Testar Xtream API</h5>
    <p style='margin-top: 0.1rem;'>
        ✅ <strong>Domínios aceitos no Smarters Pro:</strong> .ca, .io, .cc, .me, .top, .space, .in.<br>
        ❌ <strong>Domínios não aceitos:</strong> .site, .com, .lat, .live, .icu, .xyz, .online.
    </p>
""", unsafe_allow_html=True)

if "m3u_input_value" not in st.session_state:
    st.session_state.m3u_input_value = ""
if "search_name" not in st.session_state:
    st.session_state.search_name = ""

def clear_input():
    st.session_state.m3u_input_value = ""
    st.session_state.search_name = ""

def normalize_text(text):
    if not isinstance(text, str): return ""
    text = text.lower()
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')

def parse_urls(message):
    """
    Extrai credenciais de URLs M3U ou links Xtream.
    """
    # Regex melhorado para capturar a base e os parâmetros de query
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
                # Reconstrói a base: scheme://domain:port
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
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
        except Exception:
            continue
            
    return parsed_results

def get_series_details(base_url, username, password, series_id):
    try:
        url = f"{base_url}/player_api.php?username={quote(username)}&password={quote(password)}&action=get_series_info&series_id={series_id}"
        resp = requests.get(url, headers=HEADERS, verify=False, timeout=10).json()
        episodes = resp.get("episodes", {})
        if not episodes: return None
        last_season_num = max(int(k) for k in episodes.keys() if k.isdigit())
        last_episode = episodes[str(last_season_num)][-1]
        title = last_episode.get("title", "")
        match = re.search(r"S(\d+)E(\d+)", title, re.IGNORECASE)
        return match.group(0).upper() if match else f"S{last_season_num:02d}E{len(episodes[str(last_season_num)]):02d}"
    except: return None

def get_xtream_info(url_data, search_name=None):
    base, user, pwd = url_data["base"], url_data["username"], url_data["password"]
    display_base = url_data["display_base"]
    u_enc, p_enc = quote(user), quote(pwd)
    
    # Tentativa via player_api (padrão Xtream)
    api_url = f"{base}/player_api.php?username={u_enc}&password={p_enc}"
    
    res = {
        "is_json": False, "real_server": base, "exp_date": "Falha no login",
        "active_cons": "N/A", "max_connections": "N/A", "has_adult_content": False,
        "is_accepted_domain": False, "live_count": 0, "vod_count": 0, "series_count": 0,
        "search_matches": {"Canais": [], "Filmes": [], "Séries": {}}
    }

    adult_keys = ["adult", "xxx", "+18", "sex", "porn", "adulto"]

    try:
        main_resp = requests.get(api_url, headers=HEADERS, verify=False, timeout=15)
        data_json = main_resp.json()

        # Verifica se o login foi aceito (Xtream retorna user_info no sucesso)
        if "user_info" in data_json and data_json.get("user_info", {}).get("auth") != 0:
            res["is_json"] = True
            user_info = data_json.get("user_info", {})
            
            # Formatação de Data
            exp = user_info.get("exp_date")
            if exp and str(exp).isdigit():
                ts = int(exp)
                if ts == 0: res["exp_date"] = "Ilimitado"
                elif ts > 2147483647: res["exp_date"] = "Nunca expira"
                else: res["exp_date"] = datetime.fromtimestamp(ts).strftime('%d/%m/%Y')
            else:
                res["exp_date"] = "Indefinido"

            res["active_cons"] = user_info.get("active_cons", "0")
            res["max_connections"] = user_info.get("max_connections", "0")

            # Validação de Domínio
            valid_tlds = ('.ca', '.io', '.cc', '.me', '.in', '.top', '.space')
            res["is_accepted_domain"] = any(display_base.lower().endswith(tld) for tld in valid_tlds)

            # Busca de Conteúdo
            actions = {"live": "get_live_streams", "vod": "get_vod_streams", "series": "get_series"}
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_to_key = {
                    executor.submit(requests.get, f"{api_url}&action={act}", headers=HEADERS, verify=False, timeout=20): key 
                    for key, act in actions.items()
                }
                for future in as_completed(future_to_key):
                    key = future_to_key[future]
                    try:
                        resp_content = future.result().json()
                        if isinstance(resp_content, list):
                            res[f"{key}_count"] = len(resp_content)
                            
                            # Checar conteúdo adulto nos primeiros itens
                            if not res["has_adult_content"]:
                                for item in resp_content[:50]:
                                    name = normalize_text(item.get("name", ""))
                                    if any(k in name for k in adult_keys):
                                        res["has_adult_content"] = True
                                        break
                            
                            # Busca por nome
                            if search_name:
                                s_norm = normalize_text(search_name)
                                for item in resp_content:
                                    item_name = item.get("name", "")
                                    if s_norm in normalize_text(item_name):
                                        if key == "series":
                                            s_id = item.get("series_id")
                                            s_info = get_series_details(base, user, pwd, s_id)
                                            res["search_matches"]["Séries"][item_name] = s_info or "Disponível"
                                        else:
                                            cat_label = "Canais" if key == "live" else "Filmes"
                                            res["search_matches"][cat_label].append(item_name)
                    except: continue
    except:
        pass
        
    return url_data, res

# Interface Principal
with st.form(key="m3u_form"):
    m3u_message = st.text_area("Cole a URL ou lista M3U aqui", key="m3u_input_value", height=150, placeholder="http://servidor.com/get.php?username=user&password=pass&type=m3u_plus")
    search_query = st.text_input("🔍 Buscar conteúdo (Ex: Globo, Batman)", key="search_name")
    
    c1, c2 = st.columns([1,1])
    with c1: submit = st.form_submit_button("🚀 Testar Agora")
    with c2: clear = st.form_submit_button("🧹 Limpar", on_click=clear_input)

if submit and m3u_message:
    parsed = parse_urls(m3u_message)
    if not parsed:
        st.error("Nenhuma URL válida com 'username' e 'password' foi detectada.")
    else:
        with st.spinner(f"Processando {len(parsed)} servidor(es)..."):
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(get_xtream_info, url, search_query) for url in parsed]
                for future in as_completed(futures):
                    orig, info = future.result()
                    
                    status_icon = "✅" if info["is_json"] else "❌"
                    
                    with st.container(border=True):
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.write(f"{status_icon} **Servidor:** `{orig['display_base']}`")
                            st.write(f"👤 **Usuário:** `{orig['username']}`")
                            st.write(f"🔑 **Senha:** `{orig['password']}`")
                            
                            exp_date = info['exp_date']
                            color_date = "red" if "Falha" in exp_date else "green"
                            st.markdown(f"📅 **Expira:** <span style='color:{color_date}'>**{exp_date}**</span>", unsafe_allow_html=True)
                            st.write(f"🔞 **Adulto:** {'🔞 Sim' if info['has_adult_content'] else '🛡️ Não'}")
                            
                        with col_b:
                            st.write(f"📺 **Canais:** `{info['live_count']}`")
                            st.write(f"🎬 **Filmes:** `{info['vod_count']}`")
                            st.write(f"🍿 **Séries:** `{info['series_count']}`")
                            st.write(f"👥 **Conexões:** `{info['active_cons']}/{info['max_connections']}`")
                            st.write(f"📺 **Domínio TV:** {'✅' if info['is_accepted_domain'] else '❌'}")

                        if search_query and any(info["search_matches"].values()):
                            with st.expander(f"🔎 Resultados para '{search_query}'"):
                                for cat, matches in info["search_matches"].items():
                                    if matches:
                                        st.markdown(f"**{cat}**")
                                        if isinstance(matches, dict):
                                            for n, v in matches.items(): st.write(f"- {n} ({v})")
                                        else:
                                            for m in matches[:15]: st.write(f"- {m}")
                                            if len(matches) > 15: st.write(f"... e mais {len(matches)-15}")
                    st.divider()

st.caption("Nota: Otimizado para Xtream Codes API. Certificados SSL inválidos são ignorados automaticamente.")
