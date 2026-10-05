# Automatizaciones HomeLab (n8n + ejecutor local)

- `n8n/n8n_api.py`: cliente de la API pública de n8n. La clave se lee del entorno o del ámbito de usuario del registro; nunca se escribe en disco.
- `n8n/ejecutor_dispatch.py`: ejecutor de la cola de despacho. Política explícita en código: solo tipos autorizados de solo lectura se ejecutan sin aprobación individual; los tipos reservados al anfitrión (merge, deploy, dinero, borrado, mensajes a terceros, cambios de configuración, commit) conservan la aprobación. Las modificaciones no se ejecutan aquí: van por el ejecutor local con reclamación atómica.
- `n8n/salud_servicios.py` / `n8n/resumen_diario.py` / `n8n/consolidar_errores.py`: creación y verificación de los workflows de salud, resumen diario y consolidación de manejadores de error.
- `backlog/backlog_proyectos.py`: backlog consolidado por proyecto desde datos reales de GitHub (origen, prioridad, dependencia, criterio de aceptación, ejecutor).
- `cola/cola_tareas.py`: cola local con reclamación atómica (SQLite) y programador único.

Datos personales y credenciales sustituidos por marcadores. Los identificadores de credenciales de n8n aparecen como marcadores.
