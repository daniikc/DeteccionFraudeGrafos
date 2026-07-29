# Detección de fraude financiero utilizando grafos

Código correspondiente al Trabajo Fin de Máster **«Detección de Fraude Financiero utilizando
Grafos»** (Máster Universitario en Inteligencia Artificial, Universidad Tecnológica
Atlántico-Mediterráneo, 2026).

El trabajo aborda la detección de blanqueo de capitales reformulando el problema como una
**clasificación de nodos** sobre un grafo transaccional, y compara cuatro arquitecturas de
complejidad creciente para cuantificar qué aporta exactamente la información estructural:

| # | Modelo | Información disponible |
|---|--------|------------------------|
| 1 | XGBoost sin grafo | 15 variables tabulares |
| 2 | XGBoost con grafo | + 16 métricas estructurales explícitas |
| 3 | PNA en solitario | 33 variables + paso de mensajes |
| 4 | Híbrido PNA + XGBoost | 31 variables explícitas + 16 embeddings de la PNA |

Cada transición aísla una única fuente de información, de modo que las diferencias observadas
son atribuibles a ella y no al ajuste.

---

## Estructura del repositorio

```
DeteccionFraudeGrafosHibrido/
├── README.md
├── requirements.txt
├── .gitignore
├── generar_dataset_solo_patrones.py    Paso 1 · reetiquetado del conjunto
├── Script_4_modelos.ipynb              Paso 2 · estudio comparativo completo
├── datos/
│   ├── README.md                       Cómo obtener el conjunto original
│   └── patterns.txt                    Patrones de blanqueo de AMLworld
└── resultados/                         Salidas generadas (vacío al clonar)
```

Los dos archivos ejecutables quedan en la raíz y se lanzan en ese orden. Las carpetas separan
lo que no es código: `datos/` contiene el conjunto —no versionado por su tamaño— y
`resultados/` recoge las salidas que el cuaderno regenera en cada ejecución.

---

## Instalación

Entorno de referencia: **Python 3.10**.

```bash
git clone https://github.com/daniikc/DeteccionFraudeGrafosHibrido.git
cd DeteccionFraudeGrafosHibrido

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

Si la instalación conjunta de PyTorch Geometric falla, instálese en dos pasos:

```bash
pip install torch==2.5.1
pip install torch-geometric==2.6.1
```

> ### Aviso sobre la versión de XGBoost
>
> `requirements.txt` fija **`xgboost==2.1.4`** y no debe actualizarse a la rama 3.x. Desde la
> versión 3.0, XGBoost serializa el parámetro `base_score` como cadena de lista (`'[5E-1]'`)
> en lugar de como número real; el cargador de modelos de SHAP intenta convertirlo con
> `float()` y aborta, lo que impide construir `TreeExplainer` y deja sin efecto todo el
> análisis de interpretabilidad. La corrección existe en SHAP, pero solo en versiones que
> exigen Python ≥ 3.11.
>
> El pin no altera los resultados: algoritmo, hiperparámetros y predicciones son equivalentes.
> La primera celda del cuaderno comprueba la versión y detiene la ejecución si detecta una
> incompatible, para que el problema no aparezca al final del proceso.

---

## Pasos seguidos

### Paso 0 · Obtener el conjunto de datos

El conjunto original no se incluye en el repositorio por su tamaño. Procede del conjunto
sintético **IBM AMLworld**, variante *HI*, publicado por Altman et al. (2023). Las
instrucciones de descarga están en [`datos/README.md`](datos/README.md).

Al terminar debe existir `datos/Transacciones_mod_hi.csv`, con las columnas de importe
normalizadas a euros (`Amount_Paid_EUR`, `Amount_Received_EUR`) y el indicador
`Distinto_banco`.

### Paso 1 · Reetiquetado: conservar solo los patrones estructurales

```bash
python generar_dataset_solo_patrones.py \
       datos/patterns.txt \
       datos/Transacciones_mod_hi.csv \
       datos/Transacciones_solo_patrones.csv
```

El conjunto original marca como blanqueo tanto las operaciones que forman parte de un patrón
estructural —recogidas en `patterns.txt`— como las de la fase de **integración**, que son
movimientos aislados hacia la economía formal. Estas últimas no dejan huella topológica
alguna: desde la red resultan indistinguibles de cualquier operación legítima, y ninguna
métrica de grafo puede detectarlas.

El script conserva por tanto la etiqueta positiva en las transacciones pertenecientes a
cualquiera de los ocho tipos de patrón y **reetiqueta a 0 las de integración**. El cruce se
realiza por marca de tiempo, cuenta de origen, cuenta de destino e importes.

**Ninguna fila se elimina.** Las transacciones reetiquetadas permanecen en el conjunto y
siguen contribuyendo a la topología del grafo: solo cambia la variable objetivo. Esto es
esencial para que el grafo sobre el que se calculan las métricas siga siendo el real.

Distribución de los 3.209 movimientos que conservan la etiqueta positiva, según el tipo de
patrón al que pertenecen:

| Patrón | Bloques | Transacciones |
|---|---:|---:|
| Gather-scatter | 51 | 716 |
| Scatter-gather | 44 | 626 |
| Stack | 43 | 466 |
| Fan-out | 48 | 342 |
| Fan-in | 40 | 318 |
| Cycle | 54 | 287 |
| Bipartite | 49 | 263 |
| Random | 41 | 191 |
| **Total** | **370** | **3.209** |

### Paso 2 · Ejecutar el estudio comparativo

```bash
jupyter notebook Script_4_modelos.ipynb
```

Ejecútense las celdas en orden. El cuaderno debe lanzarse **desde la raíz del repositorio**:
lee de `datos/` y escribe en `resultados/` mediante rutas relativas.

Fases del cuaderno:

1. **Carga y filtrado.** Se descartan las transacciones de una cuenta consigo misma, que no
   aportan información estructural y distorsionan el cálculo de los grados.
2. **Detección de ciclos temporales.** Se buscan caminos cerrados de longitud 3 a 8 con
   marcas de tiempo crecientes en los que el importe se conserva aproximadamente (cociente
   entre el final y el inicial dentro del intervalo 0,75–1,25).
3. **Construcción de la tabla de nodos.** Una función unificada calcula las 33 variables de
   cada cuenta, de modo que los cuatro modelos parten de la misma tabla y toman después su
   subconjunto de columnas.
4. **Partición temporal.** Días 1–3 para entrenamiento, días 4–6 para prueba. No es una
   partición aleatoria: reproduce la situación real en que el modelo debe generalizar a
   operativa futura.
5. **Entrenamiento y evaluación** de los cuatro modelos bajo un protocolo común: idéntico
   espacio de hiperparámetros para los tres XGBoost e idéntica arquitectura de red (dos capas
   PNA, 32 y 16 dimensiones, agregadores media/máximo/mínimo/desviación típica, escaladores
   identidad/amplificación/atenuación, *dropout* del 30 %) en los modelos 3 y 4.
6. **Análisis SHAP** del modelo híbrido.

> La celda de construcción de nodos es la más costosa del cuaderno: la detección de ciclos
> recorre el grafo completo de cada partición y puede tardar varios minutos.

---

## Decisiones metodológicas relevantes

**Propagación de las etiquetas a los nodos.** El conjunto está etiquetado a nivel de
transacción, pero la unidad de análisis es la cuenta. Se adopta un criterio inclusivo: una
cuenta se etiqueta como fraudulenta si participa, **como emisora o como receptora**, en al
menos una transacción marcada dentro de la ventana temporal. En un ciclo o en una estructura
de tipo *gather-scatter* ninguna cuenta implicada ocupa una posición accesoria, y excluir a
las intermediarias supondría descartar aquellas cuya posición resulta más reveladora. La
contrapartida es que la clase positiva no representa el conjunto de cuentas controladas por
una organización, sino el de cuentas implicadas estructuralmente en un patrón.

**Aristas dirigidas en el paso de mensajes.** El tensor de aristas conserva el sentido
económico de la operación: cada cuenta agrega información de aquellas que le envían fondos.
Se ensayó una variante con aristas en ambos sentidos, bajo la hipótesis de que permitiría a
las cuentas dispersoras recibir información de sus destinatarios, pero el rendimiento
resultó inferior y se descartó. La interpretación más plausible es que la direccionalidad
constituye en sí misma una señal discriminante: introducir la arista inversa la diluye,
igualando el vecindario de una cuenta receptora y el de una emisora.

**Tratamiento del desbalanceo.** No se recurre a remuestreo (SMOTE, submuestreo aleatorio),
sino a los mecanismos de ponderación de clases propios de cada algoritmo —`scale_pos_weight`
en XGBoost, `pos_weight` en la función de pérdida de la PNA— complementados con un ajuste
posterior del umbral de decisión.

**Protocolo del umbral.** El umbral **no** se elige sobre el conjunto de prueba. Se aparta un
25 % estratificado del entrenamiento, se ajusta el modelo sin esas cuentas, se selecciona el
umbral que maximiza el F1 de la clase minoritaria sobre ellas y solo entonces se reentrena
con todo el conjunto. El PR-AUC, que es la métrica principal, es independiente del umbral y
por tanto ajeno a esta decisión: eso lo convierte en el criterio limpio para comparar las
cuatro arquitecturas.

**Ausencia de estandarización en los modelos de árboles.** Solo la PNA recibe variables
estandarizadas. El escalador se ajusta **exclusivamente** con los días de entrenamiento.

---

## Salidas generadas

| Archivo | Contenido |
|---|---|
| `resultados/resultados_comparativa.csv` | ROC-AUC, PR-AUC y F1 minoritaria de los cuatro modelos |
| `resultados/comparativa_4_modelos.png` | Gráfico comparativo (Figura 5 de la memoria) |
| `resultados/shap_importancia_barras.png` | Importancia media \|SHAP\| del modelo híbrido |
| `resultados/shap_beeswarm.png` | Distribución de valores SHAP (Figura 6 de la memoria) |
| `resultados/resultados_shap.csv` | Importancia media por variable y peso relativo de los embeddings |

### Valores publicados en la memoria

| Modelo | PR-AUC | F1 minoritaria | Recall | Precisión |
|---|---:|---:|---:|---:|
| 1 · XGBoost sin grafo | 0,2538 | 0,2113 | 0,13 | 0,68 |
| 2 · XGBoost con grafo | 0,2943 | 0,1972 | 0,11 | 0,81 |
| 3 · PNA en solitario | 0,2615 | 0,2772 | 0,26 | 0,30 |
| 4 · Híbrido PNA + XGBoost | 0,4439 | 0,4182 | 0,28 | 0,82 |

> Son las cifras que reproduce este cuaderno con la semilla fijada (`SEED = 42`). Pueden
> aparecer variaciones menores en el modelo 3 y en el híbrido según la versión de PyTorch y el
> dispositivo de cálculo, ya que algunas operaciones de agregación no son deterministas en
> GPU.

---

## Limitaciones conocidas

- Los resultados proceden de **una única ejecución** de cada modelo, sin repeticiones con
  distintas semillas, por lo que no van acompañados de una estimación de su variabilidad.
- En el modelo híbrido, la red se ajusta con las etiquetas del conjunto de entrenamiento y
  sus embeddings alimentan después a un clasificador entrenado sobre ese mismo conjunto. La
  separación temporal garantiza que ninguna información de los días 4–6 interviene en ninguna
  etapa, pero no puede descartarse que la ganancia real sea algo menor que la observada. Un
  protocolo de validación cruzada anidada para generar los embeddings lo resolvería.
- La detección de ciclos emplea una búsqueda **voraz**: en cada arista toma la primera
  transacción posterior a la anterior del recorrido, de modo que puede descartar ciclos
  válidos alcanzables con otra elección. `En_Ciclo` infraestima, por tanto.
- Al recorrer el paso de mensajes únicamente las aristas entrantes, las cuentas sin
  operaciones de entrada no reciben mensaje alguno y su representación se reduce a una
  transformación de sus propias variables. Las métricas explícitas del vecindario
  (`MaxNbr_*`, `MeanNbr_*`, `StdNbr_*`, `Reciprocity`) cubren parcialmente esa carencia.
- Las cuentas con una sola operación reciben `0` en `Burstiness` y en `Amt_Std`, valor que en
  la escala de la primera métrica corresponde a un comportamiento neutro.
- La intermediación y la cercanía se definen en la memoria pero no se calculan, por su coste
  computacional sobre un grafo de esta magnitud.

---

## Cita

```
Kock Cabrera, D. H. (2026). Detección de fraude financiero utilizando grafos
[Trabajo Fin de Máster]. Universidad Tecnológica Atlántico-Mediterráneo.
```

## Conjunto de datos

```
Altman, E., Blanuša, J., von Niederhäusern, L., Egressy, B., Anghel, A., y Atasu, K. (2023).
Realistic synthetic financial transactions for anti-money laundering models.
Advances in Neural Information Processing Systems, 36. https://arxiv.org/abs/2306.16424
```

## Licencia

Código publicado con fines académicos. El conjunto de datos original se rige por la licencia
de su distribución de origen.
