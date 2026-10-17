# NHANES: salud cardiovascular y metabólica (Regresión lineal + Ridge/Lasso)

Dataset consolidado de **NHANES** (National Health and Nutrition Examination Survey, CDC) para trabajar dos preguntas:

1. **Regresión lineal:** predecir la presión arterial sistólica (`sbp`) o el IMC (`bmi`) a partir de la edad, el colesterol total, los triglicéridos y la glucosa en ayunas.
2. **Regularización (Ridge / Lasso):** meter todo el panel de biomarcadores de laboratorio (lípidos, minerales, PCR, función hepática y renal, hemograma), muy correlacionados entre sí, y ver cuáles conserva Lasso.

Los datos se descargan **directamente de la web del CDC**, sin claves, sin paquetes externos y sin buscar archivos a mano.

## Cómo empezar

```bash
pip install -r requirements.txt
python get_data.py                 # ciclos 2015-2016 + 2017-2018 (por defecto)
python get_data.py 2017-2018       # o un solo ciclo
```

La primera ejecución descarga ~37 MB de archivos `.xpt` a `data/raw/`, que quedan en caché. Después genera:

| Archivo | Contenido |
|---|---|
| `data/nhanes_cardiometabolic_clean.csv` | **El que hay que usar.** 10.739 adultos (≥ 20 años) × 73 columnas con nombres legibles |
| `data/nhanes_cardiometabolic_raw.csv` | Todos los participantes y las 287 columnas originales del CDC, unidas por `SEQN` |

### Cargar otros archivos de NHANES

`nhanes.py` sirve para cualquier componente y ciclo (1999-2023):

```python
import nhanes
vitd = nhanes.load("VID", "2017-2018")                          # vitamina D
df = nhanes.load_many(["DEMO", "BMX", "FERTIN"], ["2015-2016", "2017-2018"])
```

Los nombres de componente (`DEMO`, `BIOPRO`, `FERTIN`...) son los del [buscador de variables del CDC](https://wwwn.cdc.gov/nchs/nhanes/search/default.aspx).

## Variables del dataset limpio

| Grupo | Columnas |
|---|---|
| Diseño muestral | `seqn`, `cycle`, `psu`, `strata`, `wt_mec`, `wt_fasting`, `fasting_subsample` |
| Demografía | `age` (máx. 80), `sex`, `race_eth`, `education`, `income_poverty_ratio` |
| Exploración | `sbp`, `dbp` (media de hasta 4 lecturas), `sbp1`, `dbp1` (1.ª lectura = `BPXSY1`/`BPXDI1`), `pulse`, `weight`, `height`, `bmi`, `waist` |
| Cuestionarios | `smoking` (never/former/current), `diabetes_dx`, `hypertension_dx`, `bp_meds`, `chol_meds` |
| Lípidos y glucosa | `total_chol`, `hdl`, `ldl`\*, `triglycerides`\*, `glucose_fasting`\*, `insulin`\*, `hba1c` |
| Inflamación | `hs_crp` (proteína C reactiva ultrasensible) |
| Hígado | `alt`, `ast`, `alp`, `ggt`, `ldh`, `bilirubin`, `albumin`, `total_protein`, `globulin` |
| Riñón | `creatinine`, `bun`, `uric_acid` |
| Electrolitos y minerales | `sodium`, `potassium`, `chloride`, `bicarbonate`, `calcium`, `phosphorus`, `iron`, `osmolality` |
| Bioquímica sin ayuno | `glucose_serum`, `chol_serum`, `trig_serum`, `cpk` |
| Hemograma | `wbc`, `lymph_pct`, `mono_pct`, `neut_pct`, `eos_pct`, `baso_pct`, `rbc`, `hemoglobin`, `hematocrit`, `mcv`, `mch`, `mchc`, `rdw`, `platelets`, `mpv` |

Unidades: las convencionales de EE. UU. (mg/dL para lípidos y glucosa, mmHg, kg, cm, mg/L para PCR).
Los códigos "No sabe" / "Se niega" ya están convertidos a `NaN`.

\* **Submuestra en ayunas.** Triglicéridos, LDL, glucosa en ayunas e insulina solo se midieron en la sesión de mañana (`fasting_subsample == True`, ~4.500 adultos). El modelo `sbp ~ age + total_chol + triglycerides + glucose_fasting` tiene **4.488 casos completos**.

## Cosas a tener en cuenta

* **Multicolinealidad (a propósito).** Hay pares casi redundantes, justo lo que necesita Ridge/Lasso: `total_chol`–`chol_serum` (r = 0,99), `hemoglobin`–`hematocrit` (0,97), `glucose_fasting`–`hba1c` (0,85), `sodium`–`osmolality` (0,81), `ast`–`alt` (0,73). Además `globulin = total_protein − albumin` es una combinación lineal exacta.
* **Medicación.** Quien toma antihipertensivos (`bp_meds`) o estatinas (`chol_meds`) tiene la PA o el colesterol tratados; conviene incluirlo como control o excluir a esas personas.
* **Asimetría.** `triglycerides`, `insulin`, `hs_crp`, `ggt`, `alt` y `cpk` tienen colas largas: mejor usar el logaritmo. Estandariza siempre antes de Ridge/Lasso.
* **Pesos muestrales.** NHANES no es una muestra aleatoria simple: sobrerrepresenta algunos grupos. Para estimar prevalencias o medias poblacionales usa `wt_mec` (o `wt_fasting` con variables de la submuestra en ayunas) junto con `psu` y `strata`. Al combinar ciclos el peso ya está dividido entre el número de ciclos, como indica el CDC. Para un ejercicio de regresión sin pesos es habitual, pero hay que mencionarlo.
* **Ciclos.** 2015-2016 y 2017-2018 tienen exactamente las mismas variables. A partir de 2017-2020 (pre-pandemia) y 2021-2023 la presión se mide con oscilómetro (`BPXO`, sin `BPXSY1`) y falta parte del panel, así que `get_data.py` no está pensado para esos ciclos.

## Fuente

Centers for Disease Control and Prevention (CDC), National Center for Health Statistics (NCHS). *National Health and Nutrition Examination Survey Data*. Hyattsville, MD: U.S. Department of Health and Human Services. <https://wwwn.cdc.gov/nchs/nhanes/>. Los datos son de dominio público.
