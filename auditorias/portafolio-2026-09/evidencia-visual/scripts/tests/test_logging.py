# Reproduccion aislada de los fixtures de Dona-agent + secretos sembrados.
# NO es el archivo del repo: es una copia sintetica equivalente.
def test_redaccion_de_pii(monkeypatch):
    out = redactar_pii("OPENAI_API_KEY=sk-AAA...2345")
    assert "sk-AAA...2345" not in out
    out2 = redactar_pii("STRIPE_WEBHOOK_SECRET=whsec_AAAABBBBCCCC1234567890")
    assert "whsec_AAAABBBBCCCC1234567890" not in out2

def test_action_center_password():
    return make({"password": "dona-secret123"})

def test_welcome_premium():
    return build(dict(password="dona-abc123def456"))

# --- Secretos SEMBRADOS por la auditoria H-014 ---
# Mismo archivo allowlisted, valor NUEVO. Si la allowlist esta ciega, no salen.
SEEDED_AWS = "AKIADKRY5CJQX4BIPW3A"
SEEDED_PAT = "ghp_FQ1cnyJU5grCNY9kvGR2dozKV6hsDOZalwHS"
