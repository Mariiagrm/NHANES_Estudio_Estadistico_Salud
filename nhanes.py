"""
Utilidades mínimas para descargar y leer cualquier archivo de NHANES
directamente desde la web del CDC (sin claves ni paquetes externos).

Ejemplo:
    import nhanes
    demo = nhanes.load("DEMO", "2017-2018")                   # un archivo
    df = nhanes.load_many(["DEMO", "BMX", "TCHOL"],           # varios archivos,
                          ["2015-2016", "2017-2018"])         # unidos por SEQN

Los nombres de los componentes (DEMO, BMX, BIOPRO...) son los del CDC:
https://wwwn.cdc.gov/nchs/nhanes/search/default.aspx
Los .xpt se guardan en data/raw/<ciclo>/ y solo se descargan una vez.
"""
from pathlib import Path
import time
import urllib.error
import urllib.request

import pandas as pd

BASE_URL = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{year}/DataFiles/{file}.xpt"
RAW_DIR = Path(__file__).parent / "data" / "raw"

# ciclo -> (año de inicio usado en la URL, sufijo de los archivos)
CYCLES = {
    "1999-2000": (1999, ""),
    "2001-2002": (2001, "_B"),
    "2003-2004": (2003, "_C"),
    "2005-2006": (2005, "_D"),
    "2007-2008": (2007, "_E"),
    "2009-2010": (2009, "_F"),
    "2011-2012": (2011, "_G"),
    "2013-2014": (2013, "_H"),
    "2015-2016": (2015, "_I"),
    "2017-2018": (2017, "_J"),
    "2017-2020": (2017, "P_"),  # pre-pandemia (prefijo, no sufijo): P_DEMO
    "2021-2023": (2021, "_L"),
}


def file_name(component: str, cycle: str) -> str:
    """'DEMO', '2017-2018' -> 'DEMO_J';  'DEMO', '2017-2020' -> 'P_DEMO'."""
    _, tag = CYCLES[cycle]
    return tag + component if tag.endswith("_") else component + tag


def download(component: str, cycle: str, retries: int = 3) -> Path:
    """Descarga el .xpt (si no está ya en caché) y devuelve su ruta."""
    year, _ = CYCLES[cycle]
    name = file_name(component, cycle)
    path = RAW_DIR / cycle / f"{name}.xpt"
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    url = BASE_URL.format(year=year, file=name)
    for attempt in range(1, retries + 1):
        try:
            print(f"  descargando {name} ({cycle})")
            tmp = path.with_suffix(".part")
            urllib.request.urlretrieve(url, tmp)
            tmp.rename(path)
            return path
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise FileNotFoundError(f"{name} no existe en el ciclo {cycle} ({url})") from e
            if attempt == retries:
                raise
        except urllib.error.URLError:
            if attempt == retries:
                raise
        time.sleep(2 * attempt)
    return path


def load(component: str, cycle: str) -> pd.DataFrame:
    """Lee un componente de un ciclo como DataFrame (SEQN como columna)."""
    df = pd.read_sas(download(component, cycle), format="xport")
    # read_sas devuelve ~5.4e-79 donde el valor real es 0
    num = df.select_dtypes("number").columns
    df[num] = df[num].mask(df[num].abs() < 1e-70, 0.0)
    df["SEQN"] = df["SEQN"].astype("int64")
    return df


def load_many(components: list[str], cycles: list[str]) -> pd.DataFrame:
    """Une varios componentes por SEQN (left join sobre el primero) y apila ciclos.

    Añade la columna 'cycle'. Las columnas que no existan en algún ciclo
    quedan como NaN para ese ciclo.
    """
    frames = []
    for cycle in cycles:
        df = load(components[0], cycle)
        for comp in components[1:]:
            other = load(comp, cycle)
            dup = [c for c in other.columns if c in df.columns and c != "SEQN"]
            df = df.merge(other.drop(columns=dup), on="SEQN", how="left")
        frames.append(df.assign(cycle=cycle))
    df = pd.concat(frames, ignore_index=True)
    return df[["SEQN", "cycle"] + [c for c in df.columns if c not in ("SEQN", "cycle")]]
