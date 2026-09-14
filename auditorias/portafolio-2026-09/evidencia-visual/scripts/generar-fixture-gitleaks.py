#!/usr/bin/env python3
"""Genera el fixture aislado para probar la allowlist de gitleaks.

No contiene literales con forma de secreto: los construye por partes en runtime,
para que el propio generador no dispare escáneres ni redacciones al escribirlo.
"""
import os

d = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(d, 'tests'), exist_ok=True)
os.makedirs(os.path.join(d, 'tests', '__pycache__'), exist_ok=True)
os.makedirs(os.path.join(d, 'landing', '.next', 'dev'), exist_ok=True)

ALNUM_UP = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'


def fill(n, alphabet, step, seed):
    return ''.join(alphabet[(i * step + seed) % len(alphabet)] for i in range(n))


# --- Fixtures REALES de Dona-agent (valores ya publicos en su repo publico) ---
fixture_openai = 'sk-' + 'A' * 3 + '.' * 3 + '2345'          # == sk-AAA...2345
fixture_whsec = 'whsec' + '_' + 'A' * 4 + 'B' * 4 + 'C' * 4 + '1234567890'
fixture_pass1 = 'dona-' + 'secret' + '123'
fixture_pass2 = 'dona-' + 'abc123def456'

# --- Secretos SEMBRADOS: valor NUEVO, forma valida para su regla ------------
seeded_aws = 'AKIA' + fill(16, ALNUM_UP, 7, 3)
seeded_pat = 'ghp' + '_' + fill(36, ALNUM_UP + 'abcdefghijklmnopqrstuvwxyz', 11, 5)

lines = [
    '# Reproduccion aislada de los fixtures de Dona-agent + secretos sembrados.',
    '# NO es el archivo del repo: es una copia sintetica equivalente.',
    'def test_redaccion_de_pii(monkeypatch):',
    '    out = redactar_pii("OPENAI_API_KEY=' + fixture_openai + '")',
    '    assert "' + fixture_openai + '" not in out',
    '    out2 = redactar_pii("STRIPE_WEBHOOK_SECRET=' + fixture_whsec + '")',
    '    assert "' + fixture_whsec + '" not in out2',
    '',
    'def test_action_center_password():',
    '    return make({"password": "' + fixture_pass1 + '"})',
    '',
    'def test_welcome_premium():',
    '    return build(dict(password="' + fixture_pass2 + '"))',
    '',
    '# --- Secretos SEMBRADOS por la auditoria H-014 ---',
    '# Mismo archivo allowlisted, valor NUEVO. Si la allowlist esta ciega, no salen.',
    'SEEDED_AWS = "' + seeded_aws + '"',
    'SEEDED_PAT = "' + seeded_pat + '"',
    '',
]

with open(os.path.join(d, 'tests', 'test_logging.py'), 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(lines))

# Artefacto generado y no versionado (el ruido que aparecio al correr `next dev`)
with open(os.path.join(d, 'landing', '.next', 'dev', 'x.json'), 'w', encoding='utf-8') as fh:
    fh.write('{"encryptionKey":"' + fill(32, ALNUM_UP + 'abcdefghijklmnopqrstuvwxyz', 5, 9) + '"}\n')

# Artefacto __pycache__ (el ruido que aparecio al correr pytest)
with open(os.path.join(d, 'tests', '__pycache__', 'test_logging.cpython-312.pyc'), 'wb') as fh:
    fh.write(b'placeholder ' + fixture_openai.encode())

print('generado en', d)
print('seeded_aws len', len(seeded_aws), '| seeded_pat len', len(seeded_pat))
