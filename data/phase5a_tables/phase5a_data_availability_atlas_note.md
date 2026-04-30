# Phase 5A — atlas maestro de disponibilidad de datos

## 1. Propósito

Saber qué preguntas físicas permite el material disponible antes de formular
hipótesis. Este atlas no calcula residuos nuevos, no abre payloads nuevos y no
modifica los CSVs/informes ya generados. Es un mapa derivado de:

- `phase5a_source_inventory.csv`
- `phase5a_event_inventory.csv`
- `phase5a_primary_candidates.csv`
- `phase5a_missing_or_unclear.csv`
- `phase5a_three_candidate_audit.md`
- `phase5a_domega_convention_audit.md`
- `phase5a_s190521r_residual_221_note.md` y `phase5a_s190521r_acceptance_check.md`
- `phase5a_pyring_221_selection_triage.md`, `phase5a_pyring_221_next3_audit_plan.md`,
  `phase5a_pyring_221_next3_hdf5_audit.md`, `phase5a_pyring_221_verified_overrides.csv`
- `phase5a_pyring_220_availability_triage.md`
- `phase5a_gwtc3_v2_rin_payload_220_search.md` y
  `phase5a_gwtc3_v2_rin_payload_220_candidates.csv`
- `phase5a_pyring_qnmrf_payload_220_search.md` y
  `phase5a_pyring_qnmrf_payload_220_candidates.csv`
- `pyring_221_cohort_residuals_summary.csv`

## 2. Resumen global

- Filas totales del atlas: **376**
- Eventos únicos (incluyendo `population_o4a` y `cohort_pyring_221`): **53**
  (26 S-events GWTC-3 v2-rin + 22 GW O4a + 2 QNMRF + 3 externos
  [GW150914, GW190521, GW250114])
- Combinaciones únicas de payload + fichero/informe: **355**
- Conteos por `allowed_physical_question`:
  - `residual_220_joint`: **0**
  - `residual_220_unpaired_composition`: **70**
  - `residual_221_joint`: **53**
  - `method_validation_only`: **20**
  - `remnant_only_crosscheck`: **48**
  - `no_residual_allowed`: **185**

## 3. Tabla resumen por pregunta física permitida

| pregunta física permitida | filas | dónde aparece principalmente | observable_family típico |
|---|---:|---|---|
| `residual_220_joint` | 0 | n/a | n/a |
| `residual_220_unpaired_composition` | 70 | GWTC-3 v2-rin DS_1mode_10M (26) + O4a DS_1mode_10M (22) + O4a DS_2mode_10M (22) | `free_frequency` |
| `residual_221_joint` | 53 | GWTC-3 v2-rin Kerr_221_domega_221_0M (26, parcial) + Kerr_221_domega_dtau_221_0M (26, full) + cohort_pyring_221 (1) | `fractional_deviation` |
| `method_validation_only` | 20 | pSEOBNRv4HM presente en 18 eventos GWTC-3 + 2 hierarchical O4a | `fractional_deviation` (joint pero convención no documentada localmente) |
| `remnant_only_crosscheck` | 48 | MMRDNP_15M (26 GWTC-3) + events_summary_file.h5 (22 O4a) | `remnant_only` |
| `no_residual_allowed` | 185 | Kerr_220_0M / Kerr_220_10M / Kerr_221_0M (GR-fixed, todos los eventos), TEOB ..._domega_220_0.0M / ..._domega_dtau_220_0.0M (no hay Mf/af joint), Kerr_221_dtau_221_0M (sin domega), pSEOBNRv4HM ausente, QNMRF, externos | `gr_fixed_kerr`, `fractional_deviation` con bloqueo unpaired, `unclear` |

## 4. Preguntas físicas actualmente permitidas

1. **`residual_221_joint` (modo overtone 221)** — sólo en `LVK_GWTC3_TGR` /
   `pyRing` / `Kerr_221_domega_dtau_221_0M`. Para 5 eventos hay verificación
   directa (S150914, S170104, S170814, S170823, S190521r) y residual ya
   computado en `pyring_221_cohort_residuals_summary.csv`. Para los otros 21
   eventos del release el bloqueo es `manual_hdf5_audit` antes de promover a
   `verified=yes`. **Caveat:** modo overtone, no fundamental; resultado
   dominado por prior amplio; cohorte pequeña.

2. **`residual_220_unpaired_composition` (modo fundamental 220)** —
   composición posterior **no emparejada** vía DS_1mode (y DS_2mode en O4a).
   `f_t_0` / `tau_t_0` libres en el posterior DS y `Mf` / `final_spin` en otro
   posterior del mismo evento. **Caveat fuerte:** no hay correspondencia
   muestra-a-muestra; los priors y ventanas difieren.

3. **`remnant_only_crosscheck`** — uso del subconjunto MMRDNP_15M (GWTC-3) y
   `events_summary_file.h5` (O4a) sólo como anchor de remnant; no aporta
   `residual_f`.

4. **`method_validation_only`** — pSEOBNRv4HM (18 eventos GWTC-3) tiene joint
   `final_mass`/`final_spin`/`domega220`/`dtau220` pero la convención exacta
   de `domega220`/`dtau220` no está documentada en ningún fichero local
   (HDF5, `lalinference`, wrapper Python). Usable para validación
   metodológica, no para reclamar residual del 220 hasta resolver la
   convención. Hierarchical O4a igual.

## 5. Preguntas físicas actualmente bloqueadas

1. **`residual_220_joint`** — no existe ninguna fila con `usable_for_220_joint=yes`
   en el material local. Todas las vías 220 son: (a) GR-fixed Kerr (residual
   ≡ 0), (b) DS-libre sin Mf/af joint (unpaired), (c) TEOB con `domega_220`
   pero sin Mf/af joint (requiere fit NR externo), (d) pSEOBNRv4HM con
   joint pero convención no documentada.

2. **Cualquier afirmación poblacional homogénea** sobre
   `residual_f_220` o `residual_f_221`. Las cohortes verificadas son
   pequeñas (N=5 para 221), las DS unpaired pierden correlación posterior, y
   la cohorte O4a TEOB necesita aún el remnant joint.

3. **Reclamos de "detección de desviación"** desde la microdemo S190521r/221
   (caveat ya en `phase5a_s190521r_residual_221_note.md` y reafirmado en
   `phase5a_s190521r_acceptance_check.md`).

4. **Reclamos basados en cohortes externas** (Isi&Farr, Finch&Moore, Capano,
   Siegel/Isi/Farr, GW250114 companion): ningún payload externo está
   presente en `data/`; el bloqueo es `download_missing_release`.

5. **Reclamos basados en QNMRF** (S231028bg, S231226av): los `.pkl` no han
   sido deserializados y según los scripts contienen p-values/evidence/threshold
   dicts, no posteriors. Bloqueo: `inspect_pickle_manually`.

## 6. Regla de uso futura

Antes de formular una hipótesis nueva, consultar
`phase5a_data_availability_atlas.csv` y elegir solo preguntas con
`allowed_physical_question` distinto de `no_residual_allowed`.

Filtros recomendados:
- `usable_for_220_joint == yes` ⇒ vacío en este momento.
- `usable_for_220_unpaired == yes` ⇒ DS_1mode_10M en GWTC-3 (26) y O4a (22).
- `usable_for_221_joint == yes` ⇒ Kerr_221_domega_dtau_221_0M con
  `verification_level ∈ {hdf5_keys_verified, config_verified}` (5 eventos).
- `usable_for_population` ≠ `no` ⇒ filas exploratorias o `homogeneous_small_N`.

## 7. Conclusión específica para Phase 5A

- **`residual_220_joint = 0`** ⇒ **No existe actualmente una vía joint
  verificada para `residual_f_220`.** Cualquier intento de cuantificar una
  desviación del modo fundamental 220 a nivel posterior con muestras conjuntas
  está bloqueado por construcción del material disponible (GR-fixed Kerr,
  DS sin remnant joint, TEOB sin remnant joint, pSEOBNR convención no
  documentada).

- **`residual_220_unpaired_composition > 0` (70 filas)** ⇒ **Sí existe una
  vía exploratoria unpaired para `residual_f_220`, con caveat fuerte.** El
  pareo posterior-level no es muestra-a-muestra; las distribuciones marginales
  de `f_t_0` (DS) y `f_Kerr_220(Mf, final_spin)` (Kerr) provienen de MCMC
  distintas con priors y ventanas distintas. Sirve sólo como composición
  exploratoria, nunca como medida poblacional.

- **`residual_221_joint > 0` (53 filas, 5 con cálculo numérico ya hecho)** ⇒
  **El modo 221 sirve como control metodológico joint, no como sustituto
  de la hipótesis 220.** El overtone 221 tiene SNR efectivo bajo, prior amplio
  y un único `pyRing` reportado; demuestra que la cadena MCMC →
  `f_Kerr_lmn(M_f, χ_f)` → `residual_f` está cerrada y reproducible localmente,
  pero no responde a la pregunta sobre el modo dominante.

## 8. Próximo paso

No proponer cálculo todavía. El siguiente paso es decidir, sobre este atlas,
qué pregunta concreta del subconjunto `allowed_physical_question ≠
no_residual_allowed` se va a abordar — y qué bloqueo (`manual_hdf5_audit`,
`build_unpaired_composition`, `download_missing_release`,
`inspect_pickle_manually`) hace falta resolver primero.
