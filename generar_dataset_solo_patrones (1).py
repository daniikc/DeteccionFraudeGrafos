"""
Genera un dataset 'solo patrones':
  - Fraude que aparece en CUALQUIER bloque del patterns.txt
    (cycle, fan-out, fan-in, scatter-gather, gather-scatter,
     bipartite, stack, RANDOM)              -> se mantiene Is Laundering = 1
  - Fraude de INTEGRACION (Is Laundering=1 que NO aparece
    en ningun bloque del patterns.txt)      -> se reetiqueta a 0
  - Transacciones legitimas                 -> sin cambios

NO se borra ninguna fila: el grafo se conserva intacto, solo cambian etiquetas.
Cruce robusto por Timestamp + cuenta origen + cuenta destino + importes.

Uso:
    python generar_dataset_solo_patrones.py  patterns.txt  Transacciones_mod_hi.csv  salida.csv
"""
import re, sys, csv
from collections import Counter

# nombres de columna (ajuste si su CSV los tiene renombrados)
COL_TS, COL_FROM, COL_TO = "Timestamp", "Account", "Account.1"
COL_RECV, COL_PAID, COL_LAB = "Amount Received", "Amount Paid", "Is Laundering"

def _norm_amt(x):
    try:    return f"{float(x):.2f}"
    except (ValueError, TypeError): return str(x).strip()

def _mapa_patrones(ruta):
    """clave -> tipo de patron, para TODOS los bloques (incluido RANDOM)."""
    with open(ruta, encoding="utf-8", errors="replace") as f:
        raw = f.read()
    pmap, cur, dentro = {}, None, False
    for ln in raw.splitlines():
        s = ln.strip()
        if s.startswith("BEGIN LAUNDERING ATTEMPT"):
            m = re.search(r"-\s*([A-Z\-]+)", s); cur, dentro = (m.group(1) if m else "?"), True
        elif s.startswith("END LAUNDERING ATTEMPT"):
            cur, dentro = None, False
        elif s and dentro:
            p = s.split(",")
            pmap[(p[0].strip(), p[2].strip(), p[4].strip(),
                  _norm_amt(p[5]), _norm_amt(p[7]))] = cur
    return pmap

def generar(patterns_path, trans_in, trans_out):
    pmap = _mapa_patrones(patterns_path)
    cont = Counter()

    with open(trans_in, newline='', encoding='utf-8') as fi, \
         open(trans_out, 'w', newline='', encoding='utf-8') as fo:
        reader = csv.DictReader(fi)
        writer = csv.DictWriter(fo, fieldnames=reader.fieldnames)
        writer.writeheader()
        for row in reader:
            cont["filas_totales"] += 1
            if str(row[COL_LAB]).strip() != "1":
                writer.writerow(row); continue          # legitima -> intacta

            cont["fraude_original"] += 1
            key = (row[COL_TS].strip(), row[COL_FROM].strip(), row[COL_TO].strip(),
                   _norm_amt(row[COL_RECV]), _norm_amt(row[COL_PAID]))
            tipo = pmap.get(key, "INTEGRACION")

            if tipo == "INTEGRACION":                    # no esta en patterns -> a 0
                row[COL_LAB] = "0"
                cont["reetiquetados_a_0"] += 1
            else:                                        # cualquier patron (incl. RANDOM) -> se queda
                cont["mantenidos_patron"] += 1
                cont[f"  +{tipo}"] += 1
            writer.writerow(row)

    print("=== RESUMEN ===")
    print(f"Filas totales              : {cont['filas_totales']}")
    print(f"Fraude original (Is Laund=1): {cont['fraude_original']}")
    print(f"  -> mantenidos como fraude : {cont['mantenidos_patron']}  (todos los patrones, incl. RANDOM)")
    print(f"  -> reetiquetados a 0      : {cont['reetiquetados_a_0']}  (integracion)")
    print("\nDesglose mantenidos por tipo:")
    for k in sorted(cont):
        if k.startswith("  +"): print(f"   {k[3:]:16s} {cont[k]}")
    print(f"\nGuardado en: {trans_out}")

if __name__ == "__main__":
    generar(sys.argv[1], sys.argv[2], sys.argv[3])
