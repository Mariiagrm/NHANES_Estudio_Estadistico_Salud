"""
Construye un dataset consolidado de salud cardiovascular/metabólica a partir
de NHANES (CDC), listo para regresión lineal y Ridge/Lasso.

Fuente: National Health and Nutrition Examination Survey, descargado
directamente de https://wwwn.cdc.gov/nchs/nhanes/ (ver nhanes.py).

Uso:    python get_data.py                       # ciclos 2015-2016 + 2017-2018
        python get_data.py 2017-2018             # un solo ciclo
Salida: data/nhanes_cardiometabolic_raw.csv    (códigos originales del CDC)
        data/nhanes_cardiometabolic_clean.csv  (adultos >= 20 años, nombres legibles)
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

import nhanes

DEFAULT_CYCLES = ["2015-2016", "2017-2018"]
DATA_DIR = Path(__file__).parent / "data"
RAW_PATH = DATA_DIR / "nhanes_cardiometabolic_raw.csv"
CLEAN_PATH = DATA_DIR / "nhanes_cardiometabolic_clean.csv"

COMPONENTS = [
    "DEMO",    # demografía, pesos muestrales y diseño
    "BPX",     # presión arterial (4 lecturas)
    "BMX",     # antropometría
    "BPQ",     # cuestionario: hipertensión, colesterol y medicación
    "DIQ",     # cuestionario: diabetes
    "SMQ",     # cuestionario: tabaco
    "TCHOL",   # colesterol total
    "HDL",     # colesterol HDL
    "TRIGLY",  # triglicéridos y LDL (submuestra en ayunas)
    "GLU",     # glucosa en ayunas (submuestra en ayunas)
    "INS",     # insulina (submuestra en ayunas)
    "GHB",     # hemoglobina glicosilada
    "HSCRP",   # proteína C reactiva ultrasensible
    "BIOPRO",  # bioquímica: hígado, riñón, electrolitos, minerales...
    "CBC",     # hemograma
]

# código CDC -> nombre legible (el orden es el de las columnas del CSV limpio)
RENAME = {
    # identificación y diseño muestral
    "SEQN": "seqn", "cycle": "cycle",
    "SDMVPSU": "psu", "SDMVSTRA": "strata",
    "WTMEC2YR": "wt_mec", "WTSAF2YR": "wt_fasting",
    # demografía
    "RIDAGEYR": "age", "RIAGENDR": "sex", "RIDRETH3": "race_eth",
    "DMDEDUC2": "education", "INDFMPIR": "income_poverty_ratio",
    # exploración física
    "BPXSY1": "sbp1", "BPXDI1": "dbp1", "BPXPLS": "pulse",
    "BMXWT": "weight", "BMXHT": "height", "BMXBMI": "bmi", "BMXWAIST": "waist",
    # cuestionarios
    "SMQ020": "smoked_100_cigs", "SMQ040": "smokes_now",
    "DIQ010": "diabetes_dx", "BPQ020": "hypertension_dx",
    "BPQ050A": "bp_meds", "BPQ100D": "chol_meds",
    # lípidos, glucosa e inflamación
    "LBXTC": "total_chol", "LBDHDD": "hdl", "LBDLDL": "ldl", "LBXTR": "triglycerides",
    "LBXGLU": "glucose_fasting", "LBXIN": "insulin", "LBXGH": "hba1c",
    "LBXHSCRP": "hs_crp",
    # bioquímica (BIOPRO)
    "LBXSAL": "albumin", "LBXSTP": "total_protein", "LBXSGB": "globulin",
    "LBXSATSI": "alt", "LBXSASSI": "ast", "LBXSAPSI": "alp", "LBXSGTSI": "ggt",
    "LBXSLDSI": "ldh", "LBXSTB": "bilirubin", "LBXSCK": "cpk",
    "LBXSBU": "bun", "LBXSCR": "creatinine", "LBXSUA": "uric_acid",
    "LBXSNASI": "sodium", "LBXSKSI": "potassium", "LBXSCLSI": "chloride",
    "LBXSC3SI": "bicarbonate", "LBXSCA": "calcium", "LBXSPH": "phosphorus",
    "LBXSIR": "iron", "LBXSOSSI": "osmolality",
    "LBXSGL": "glucose_serum", "LBXSCH": "chol_serum", "LBXSTR": "trig_serum",
    # hemograma (CBC)
    "LBXWBCSI": "wbc", "LBXLYPCT": "lymph_pct", "LBXMOPCT": "mono_pct",
    "LBXNEPCT": "neut_pct", "LBXEOPCT": "eos_pct", "LBXBAPCT": "baso_pct",
    "LBXRBCSI": "rbc", "LBXHGB": "hemoglobin", "LBXHCT": "hematocrit",
    "LBXMCVSI": "mcv", "LBXMCHSI": "mch", "LBXMC": "mchc", "LBXRDW": "rdw",
    "LBXPLTSI": "platelets", "LBXMPSI": "mpv",
}

# respuestas "No sabe" / "Se niega" -> NaN
MISSING_CODES = {
    "DMDEDUC2": [7, 9], "SMQ020": [7, 9], "SMQ040": [7, 9],
    "DIQ010": [7, 9], "BPQ020": [7, 9], "BPQ050A": [7, 9], "BPQ100D": [7, 9],
}

LABELS = {
    "sex": {1: "male", 2: "female"},
    "race_eth": {1: "mexican_american", 2: "other_hispanic", 3: "nh_white",
                 4: "nh_black", 6: "nh_asian", 7: "other_multiracial"},
    "education": {1: "less_9th", 2: "9_11th", 3: "high_school",
                  4: "some_college", 5: "college_grad"},
    "diabetes_dx": {1: "yes", 2: "no", 3: "borderline"},
}
YES_NO = ["hypertension_dx", "bp_meds", "chol_meds"]


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw[raw["RIDSTATR"] == 2].copy()  # solo quienes pasaron la exploración
    for col, codes in MISSING_CODES.items():
        df[col] = df[col].mask(df[col].isin(codes))

    # medias de las lecturas de presión arterial disponibles (las 0 son no válidas)
    sy = df[["BPXSY1", "BPXSY2", "BPXSY3", "BPXSY4"]]
    di = df[["BPXDI1", "BPXDI2", "BPXDI3", "BPXDI4"]]
    sbp = sy.mask(sy == 0).mean(axis=1)
    dbp = di.mask(di == 0).mean(axis=1)

    # tabaco: never / former / current
    smoking = np.select(
        [df["SMQ020"] == 2, df["SMQ040"].isin([1, 2]), df["SMQ040"] == 3],
        ["never", "current", "former"], default=None,
    )

    df = df[list(RENAME)].rename(columns=RENAME)
    df[["sbp1", "dbp1"]] = df[["sbp1", "dbp1"]].mask(df[["sbp1", "dbp1"]] == 0)
    df.insert(df.columns.get_loc("sbp1"), "sbp", sbp.round(1))
    df.insert(df.columns.get_loc("sbp1") + 1, "dbp", dbp.round(1))
    df.insert(df.columns.get_loc("smoked_100_cigs"), "smoking", smoking)
    df = df.drop(columns=["smoked_100_cigs", "smokes_now"])

    for col, mapping in LABELS.items():
        df[col] = df[col].map(mapping)
    for col in YES_NO:
        df[col] = df[col].map({1: "yes", 2: "no"})
    # BPQ050A solo se pregunta a quien ya tiene hipertensión diagnosticada
    df.loc[df["hypertension_dx"] == "no", "bp_meds"] = "no"

    # pesos: al combinar k ciclos de 2 años se divide el peso entre k (CDC)
    k = df["cycle"].nunique()
    df["wt_mec"] /= k
    df["wt_fasting"] /= k
    df.insert(df.columns.get_loc("wt_fasting") + 1, "fasting_subsample",
              df["wt_fasting"].fillna(0) > 0)

    df = df[df["age"] >= 20]  # adultos (edad top-coded a 80)
    for col in ["seqn", "psu", "strata", "age"]:
        df[col] = df[col].astype("int64")
    return df.reset_index(drop=True)


def main() -> None:
    cycles = sys.argv[1:] or DEFAULT_CYCLES
    DATA_DIR.mkdir(exist_ok=True)
    print(f"Ciclos: {', '.join(cycles)}")
    raw = nhanes.load_many(COMPONENTS, cycles)
    raw.to_csv(RAW_PATH, index=False)

    df = clean(raw)
    df.to_csv(CLEAN_PATH, index=False)

    fasting = df["fasting_subsample"]
    print(f"\n{RAW_PATH.name}: {raw.shape[0]} filas x {raw.shape[1]} columnas")
    print(f"{CLEAN_PATH.name}: {df.shape[0]} adultos x {df.shape[1]} columnas")
    print(f"  submuestra en ayunas (triglicéridos, LDL, glucosa, insulina): {fasting.sum()}")
    cols = ["sbp", "bmi", "age", "total_chol", "triglycerides", "glucose_fasting"]
    print(f"  casos completos para sbp ~ age + total_chol + triglycerides + glucose_fasting: "
          f"{df[cols[:1] + cols[2:]].dropna().shape[0]}")


if __name__ == "__main__":
    main()
