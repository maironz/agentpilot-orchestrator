# Decision Priority — routing-generator

1. **Implementazione** → developer propone
2. **Test** → tester valida (verde = approvato)
3. **Docs** → documentazione aggiorna README
4. **Ambigui / cross-modulo** → orchestratore decide

## Scenari chiave
- Bug in adapter che rompe test → developer fix + tester valida
- Cambio struttura knowledge_base → orchestratore decide architettura
- Nuova CLI flag → developer implementa + documentazione aggiorna README
- Step non avanza → orchestratore analizza blocco
