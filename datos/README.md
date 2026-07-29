# Datos

Los conjuntos de transacciones no se incluyen en el repositorio por su tamaño (varios cientos
de MB). Esta carpeta contiene únicamente `patterns.txt` y las instrucciones para reconstruir
el resto.

## Contenido versionado

| Archivo | Descripción |
|---|---|
| `patterns.txt` | Relación de los 370 patrones de blanqueo del conjunto AMLworld HI, con las transacciones que componen cada uno. Procede de la distribución original y es el insumo del reetiquetado. |

## Archivos que debe generar el usuario

| Archivo | Cómo obtenerlo |
|---|---|
| `Transacciones_mod_hi.csv` | Conjunto original con las columnas derivadas (paso 1) |
| `Transacciones_solo_patrones.csv` | Salida del script de reetiquetado (paso 2) |

---

## Paso 1 · Descargar el conjunto original

El conjunto es **IBM AMLworld**, variante *HI* (alta incidencia de blanqueo), descrito en:

> Altman, E., Blanuša, J., von Niederhäusern, L., Egressy, B., Anghel, A., y Atasu, K. (2023).
> Realistic synthetic financial transactions for anti-money laundering models.
> *Advances in Neural Information Processing Systems, 36*. https://arxiv.org/abs/2306.16424

Está publicado por IBM en Kaggle, bajo el título *IBM Transactions for Anti Money Laundering
(AML)*. Descárguese el archivo de transacciones correspondiente a la variante HI y su
`patterns.txt` asociado.

El conjunto original tiene once columnas:

```
Timestamp, From Bank, Account, To Bank, Account.1, Amount Received,
Receiving Currency, Amount Paid, Payment Currency, Payment Format, Is Laundering
```

## Paso 2 · Añadir las columnas derivadas

El cuaderno espera tres columnas que no existen en el original:

| Columna | Definición |
|---|---|
| `Amount_Paid_EUR` | `Amount Paid` convertido a euros según `Payment Currency` |
| `Amount_Received_EUR` | `Amount Received` convertido a euros según `Receiving Currency` |
| `Distinto_banco` | Indicador binario: 1 si `From Bank` ≠ `To Bank`, 0 en caso contrario |

La normalización a una divisa común es necesaria porque el conjunto opera con once divisas
distintas y los importes no serían comparables entre transacciones. `Distinto_banco` alimenta
la variable `Frac_InterBanco` de la tabla de nodos.

Guárdese el resultado como `Transacciones_mod_hi.csv` en esta misma carpeta.

## Paso 3 · Reetiquetar

Desde la raíz del repositorio:

```bash
python generar_dataset_solo_patrones.py \
       datos/patterns.txt \
       datos/Transacciones_mod_hi.csv \
       datos/Transacciones_solo_patrones.csv
```

El script imprime un resumen que conviene conservar, porque contiene las cifras del
reetiquetado citadas en la memoria:

```
=== RESUMEN ===
Filas totales               : ...
Fraude original (Is Laund=1): ...
  -> mantenidos como fraude : ...   (todos los patrones, incl. RANDOM)
  -> reetiquetados a 0      : ...   (integracion)
```

El número de transacciones que conservan la etiqueta positiva debe coincidir con las **3.209**
que figuran en `patterns.txt`. Una cifra inferior indicaría que el cruce por marca de tiempo,
cuentas e importes no está resolviendo todas las coincidencias, en cuyo caso habría que
revisar el formato de las columnas de importe antes de continuar.
