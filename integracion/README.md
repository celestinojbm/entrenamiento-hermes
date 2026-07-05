# Integración con la app Hermes (Nous Research)

Tu app Hermes descubre skills automáticamente en `~\.hermes\skills\`. La carpeta
`hermes-skill\` de aquí contiene la skill que le enseña a Hermes el protocolo de
este centro de orquestación (leer el Kanban, ejecutar tarjetas con evidencia,
cerrar con bitácora, y delegar al puente `apply-hermes-scout`).

**No se instala sola** — instalarla es decisión tuya, porque una skill se carga
en cada sesión del agente. Para activarla:

```powershell
Copy-Item -Recurse "C:\Users\celes\entrenamiento hermes\integracion\hermes-skill" "C:\Users\celes\.hermes\skills\entrenamiento-hermes"
```

Para desactivarla:

```powershell
Remove-Item -Recurse "C:\Users\celes\.hermes\skills\entrenamiento-hermes"
```

Después de instalarla, prueba diciéndole a Hermes: **"lee el tablero y ejecuta
las tarjetas por prioridad"**.
