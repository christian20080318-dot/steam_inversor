# Principios de Inversión y Gestión de Capital para Steam

Esta base de conocimiento define las reglas financieras y heurísticas de inversión que gobiernan las decisiones del bot. Puedes añadir más documentos `.md`, `.txt` o `.pdf` en esta carpeta.

---

## 1. El Margen de Seguridad (Benjamin Graham - *El Inversor Inteligente*)
* **Regla Central:** Nunca comprar un activo por su valor justo o mediano; solo se compra cuando existe un descuento de al menos **15% a 25%** por debajo de su valor intrínseco/histórico comprobado.
* **Aplicación en Steam:** Si una caja o skin se vende normalmente a S/ 2.00, el bot solo recomendará comprar si el precio actual de liquidación o pánico cae por debajo de S/ 1.50, garantizando que tras el 15% de comisión de Valve, la ganancia neta siga siendo positiva.

---

## 2. Ley de Consumibles y Oferta Fecunda vs. Escasa
* **Activos Consumibles (Cajas y Cápsulas):** Cada vez que un jugador abre una caja o aplica una pegatina, el ítem se destruye permanentemente. La oferta total en el mundo disminuye.
* **Tesis:** Los ítems que pasan al *Rare Drop Pool* o cuyas cápsulas ya no se venden en la tienda oficial tienen una curva de oferta inelástica a mediano plazo.
* **Regla del Bot:** Se prioriza la acumulación de cajas de alta rotación (mayor liquidez y menor riesgo de retención prolongada).

---

## 3. Dimensionamiento de Posición y Criterio de Kelly Adaptado
* **Regla de No Concentración:** Nunca arriesgar más del 25% del capital total en una sola oportunidad, por atractiva que parezca.
* **Regla de Liquidez (Máximo 5% del Volumen Diario):**
  $$\text{Cantidad Máxima} = \min\left(\text{Presupuesto Asignado} / \text{Precio}, \; \text{Volumen 24h} \times 0.05\right)$$
  Esto garantiza que cuando llegue el momento de vender, puedas liquidar tu inventario en menos de 24-48 horas sin tumbar el precio del mercado.

---

## 4. Gestión de Riesgo: Operaciones Moderadas vs. Agresivas
* **Moderadas (Ilimitadas dentro de presupuesto):** Ítems con más de 500 ventas al día y descuento comprobado.
* **Agresivas (Máximo 3 al día):** Ítems con descuentos extremos (> 35%) o volumen moderado (100 - 500 ventas/día). Al limitar a 3 por día, se evita quedar sobreexpuesto a trampas de liquidez si el mercado sufre una corrección general.

---

## 5. Ciclos de Mercado en Steam
* **Efecto Fin de Semana:** Los viernes y sábados hay mayor cantidad de jugadores abriendo cajas y vendiendo drops, lo que suele empujar los precios a la baja (momento ideal de compra).
* **Efecto Mitad de Semana:** Martes a jueves la oferta disminuye y los precios se estabilizan al alza (momento óptimo para vender).
* **Grandes Rebajas:** En las Rebajas de Verano e Invierno, los jugadores malvenden activos para comprar juegos; es la ventana histórica de mayor rendimiento de compra para revender 3 semanas después.
