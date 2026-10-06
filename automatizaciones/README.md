# Automatizaciones HomeLab (n8n + ejecutor local)

- `n8n/n8n_api.py`: cliente de la API pública de n8n. La clave se lee del entorno o del ámbito de usuario del registro; nunca se escribe en disco.
- `n8n/ejecutor_dispatch.py`: ejecutor de la cola de despacho. Política explícita en código: solo tipos autorizados de solo lectura se ejecutan sin aprobación individual; los tipos reservados al anfitrión (merge, deploy, dinero, borrado, mensajes a terceros, cambios de configuración, commit) conservan la aprobación. Las modificaciones no se ejecutan aquí: van por el ejecutor local con reclamación atómica.
- `n8n/salud_servicios.py` / `n8n/resumen_diario.py` / `n8n/consolidar_errores.py`: creación y verificación de los workflows de salud, resumen diario y consolidación de manejadores de error.
- `backlog/backlog_proyectos.py`: backlog consolidado por proyecto desde datos reales de GitHub (origen, prioridad, dependencia, criterio de aceptación, ejecutor).
- `cola/cola_tareas.py`: cola local con reclamación atómica (SQLite) y programador único.

Datos personales y credenciales sustituidos por marcadores. Los identificadores de credenciales de n8n aparecen como marcadores.

## Política del ejecutor (actualizada)
Los tipos de solo lectura autorizados (`pull_request`, `issue`, `ci_run`, `verify_url`, `backlog_update`,
`notify_owner`) se ejecutan sin aprobación individual. Conservan aprobación `merge`, `deploy`, `money`,
`delete_data`, `third_party_message`, `config_change`. **Los commits y el push dentro del alcance de estos
proyectos están autorizados**; el resto de modificaciones sigue reservado. La reclamación atómica la aporta
el ejecutor local (SQLite); la concesión de las tablas de n8n es best-effort y no protege escrituras.

## Jev
`jev/jev_decide.py` conecta Jev a una decisión acotada (orden de ejecución entre opciones que entrega el
código) con umbral de confianza, fallback determinista, registro de métricas y prohibición de alterar el
conjunto de opciones. Los permisos siguen definidos por código, nunca por el modelo.
