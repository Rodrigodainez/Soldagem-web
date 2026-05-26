"""
Relação EPS X WS / RQPS — By RDS
Versão Flask (web) equivalente ao executável CustomTkinter.

Rodar local:
    pip install flask
    python app.py

Azure App Service: usa gunicorn -> app:app
"""
import base64
import json
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for

# ============================================================
# CAMINHOS — em produção (Azure) use /home/data ou variável de ambiente.
# Mantém o caminho do executável quando estiver no Windows/rede.
# ============================================================

USUARIOS_PERMITIDOS: [ 
    "R.Diniz_S@outlook.com" 
]


def verificar_acesso():
    try:
        principal = request.headers.get("X-MS-CLIENT-PRINCIPAL")

        if not principal:
            print("SEM PRINCIPAL HEADER")
            return False

        # decode correto (IMPORTANTE!)
        decoded_bytes = base64.b64decode(principal)
        decoded_str = decoded_bytes.decode("utf-8")

        user_data = json.loads(decoded_str)

        print("USER DATA:", user_data)

        user = None

        for claim in user_data.get("claims", []):
            if claim.get("typ") in ["preferred_username", "email", "name"]:
                user = claim.get("val")

        print("EMAIL EXTRAÍDO:", user)

        if not user:
            print("SEM EMAIL")
            return False

        if user.lower() not in [u.lower() for u in USUARIOS_PERMITIDOS]:
            print("USUÁRIO NÃO PERMITIDO:", user)
            return False

        return True

    except Exception as e:
        print("ERRO NA AUTENTICAÇÃO:", str(e))
        return Fa

    print("EMAIL EXTRAÍDO:", user)
    
DATA_DIR = os.environ.get("SOLDAGEM_DATA_DIR")
if not DATA_DIR:
    # fallback: pasta "data" ao lado do app
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

os.makedirs(DATA_DIR, exist_ok=True)
ARQUIVO_DADOS = os.path.join(DATA_DIR, "itens.json")
ARQUIVO_RQPS = os.path.join(DATA_DIR, "rqps_itens.json")

UNIDADES = ["Taubaté", "Macaé", "SJP", "RDO", "Drill-Quip"]
NORMAS = ["Todos", "AWS D1.1", "AWS D1.6", "ISO", "ASME"]

EPS_CAMPOS = ["eps", "rev_eps", "rqps", "rev_rqps", "wps", "unidade",
              "ws", "esp_qual", "impacto", "tt", "obs"]

RQPS_CAMPOS = ["eps", "rev_eps", "rqps", "rev_rqps", "norma", "processo",
               "mb_pno", "mb_espessura", "mb_diametro", "ma_espec", "ma_fno",
               "posicao", "progressao", "impacto", "dureza", "tt"]


# ============================================================
# PERSISTÊNCIA
# ============================================================
def _load(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERRO] Falha ao ler {path}: {e}")
        return []


def _save(path, itens):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(itens, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERRO] Não foi possível salvar {path}: {e}")


def carregar_itens():
    itens = _load(ARQUIVO_DADOS)
    for it in itens:
        if "esp_qual" not in it:
            partes = []
            if it.get("chanfro"):
                partes.append(f"Chanfro: {it['chanfro']}")
            if it.get("angulo"):
                partes.append(f"Ângulo: {it['angulo']}")
            if it.get("espessura"):
                partes.append(str(it["espessura"]))
            it["esp_qual"] = " | ".join(partes)
        for k in EPS_CAMPOS:
            it.setdefault(k, "")
    return itens


def salvar_itens(itens):
    _save(ARQUIVO_DADOS, itens)


def carregar_rqps():
    itens = _load(ARQUIVO_RQPS)
    for it in itens:
        for k in RQPS_CAMPOS:
            it.setdefault(k, "")
    return itens


def salvar_rqps(itens):
    _save(ARQUIVO_RQPS, itens)


# ============================================================
# FLASK
# ============================================================
app = Flask(__name__)


@app.route("/")
def index():
    return redirect(url_for("eps_page"))


# ---------- EPS ----------
@app.route("/eps")
def eps_page():
    acesso = verificar_acesso()

    if acesso is None:
        return "Usuário não autenticado", 401

    if acesso is False:
        return "Acesso negado", 403

    itens = carregar_itens()
    return render_template("index.html", itens=itens, unidades=UNIDADES)

@app.route("/api/eps", methods=["GET"])
def api_eps_list():
    acesso = verificar_acesso()
    if acesso is not True:
        return "Acesso negado", 403

    termo = (request.args.get("q") or "").lower()
    itens = carregar_itens()
    return jsonify(itens)


@app.route("/api/eps", methods=["POST"])
def api_eps_create():
    acesso = verificar_acesso()
    if acesso is not True:
        return "Acesso negado", 403

    data = request.get_json(force=True) or {}
    eps = (data.get("eps") or "").strip()
    if not eps:
        return jsonify({"error": "Campo EPS é obrigatório."}), 400

    novo = {k: (data.get(k) or "").strip() for k in EPS_CAMPOS}
    itens = carregar_itens()
    itens.append(novo)
    salvar_itens(itens)
    return jsonify(novo), 201

@app.route("/api/eps/<eps_id>", methods=["PUT"])
def api_eps_update(eps_id):
    acesso = verificar_acesso()
    if acesso is not True:
        return "Acesso negado", 403

    data = request.get_json(force=True) or {}
    itens = carregar_itens()

    for it in itens:
        if it.get("eps") == eps_id:
            for k in EPS_CAMPOS:
                if k in data:
                    it[k] = (data.get(k) or "").strip()

            for k in ("espessura", "chanfro", "angulo"):
                it.pop(k, None)

            salvar_itens(itens)
            return jsonify(it)

    return jsonify({"error": "EPS não encontrada."}), 404

@app.route("/api/eps/<eps_id>", methods=["DELETE"])
def api_eps_delete(eps_id):
    acesso = verificar_acesso()
    if acesso is not True:
        return "Acesso negado", 403

    itens = carregar_itens()
    novos = [it for it in itens if it.get("eps") != eps_id]

    if len(novos) == len(itens):
        return jsonify({"error": "EPS não encontrada."}), 404

    salvar_itens(novos)
    return jsonify({"ok": True})

# ---------- RQPS ----------
@app.route("/rqps")
def rqps_page():
    return render_template("rqps.html", normas=NORMAS)

@app.route("/api/rqps", methods=["GET"])
def api_rqps_list():
    acesso = verificar_acesso()
    if acesso is not True:
        return "Acesso negado", 403

    termo = (request.args.get("q") or "").lower()
    norma = request.args.get("norma") or "Todos"
    itens = carregar_rqps()

    if norma != "Todos":
        itens = [it for it in itens if it.get("norma", "") == norma]

    if termo:
        itens = [
            it for it in itens
            if any(termo in str(v).lower() for v in it.values())
        ]
        
    return jsonify(itens)

@app.route("/api/rqps", methods=["POST"])
def api_rqps_create():
    acesso = verificar_acesso()
    if acesso is not True:
        return "Acesso negado", 403
    data = request.get_json(force=True) or {}
    novo = {k: (data.get(k) or "").strip() for k in RQPS_CAMPOS}
    if not novo["eps"] and not novo["rqps"]:
        return jsonify({"error": "Informe ao menos EPS ou RQPS."}), 400
    itens = carregar_rqps()
    itens.append(novo)
    salvar_rqps(itens)
    return jsonify(novo), 201


@app.route("/api/rqps/<eps_id>/<rqps_id>", methods=["PUT"])
def api_rqps_update(eps_id, rqps_id):
    acesso = verificar_acesso()
    if acesso is not True:
        return "Acesso negado", 403
        
    data = request.get_json(force=True) or {}
    itens = carregar_rqps()
    for it in itens:
        if it.get("eps", "") == eps_id and it.get("rqps", "") == rqps_id:
            for k in RQPS_CAMPOS:
                if k in data:
                    it[k] = (data.get(k) or "").strip()
            salvar_rqps(itens)
            return jsonify(it)
    return jsonify({"error": "Registro não encontrado."}), 404

@app.route("/api/rqps/<eps_id>/<rqps_id>", methods=["DELETE"])
def api_rqps_delete(eps_id, rqps_id):
    acesso = verificar_acesso()
    if acesso is not True:
        return "Acesso negado", 403
        
    itens = carregar_rqps()
    novos = [it for it in itens
             if not (it.get("eps", "") == eps_id and it.get("rqps", "") == rqps_id)]
    if len(novos) == len(itens):
        return jsonify({"error": "Registro não encontrado."}), 404
    salvar_rqps(novos)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
