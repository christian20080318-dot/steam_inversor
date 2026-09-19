"""
Módulo de Seguimiento y Clasificación de Drop Pools de Counter-Strike 2 y Activos de Steam.
Permite al bot distinguir entre activos inflacionarios (caen semanalmente)
y activos deflacionarios con oferta decreciente (reserva de valor a mediano/largo plazo).
"""

# Base de conocimiento del estado de las cajas en Counter-Strike 2
PRIME_ACTIVE_CASES = {
    "Gallery Case",
    "Kilowatt Case",
    "Revolution Case",
    "Recoil Case",
    "Dreams & Nightmares Case"
}

RARE_DROP_CASES = {
    "Fracture Case",
    "Snakebite Case",
    "Clutch Case",
    "Prisma Case",
    "Prisma 2 Case",
    "Danger Zone Case",
    "Horizon Case",
    "CS20 Case",
    "Spectrum Case",
    "Spectrum 2 Case",
    "Gamma Case",
    "Gamma 2 Case",
    "Chroma Case",
    "Chroma 2 Case",
    "Chroma 3 Case",
    "Glove Case",
    "Operation Phoenix Weapon Case",
    "Operation Vanguard Weapon Case",
    "Operation Breakout Weapon Case",
    "Winter Offensive Weapon Case",
    "Revolver Case",
    "Shadow Case",
    "Falchion Case",
    "Huntsman Weapon Case"
}

DISCONTINUED_ASSETS = {
    # Cajas de Operaciones
    "Operation Riptide Case",
    "Operation Broken Fang Case",
    "Shattered Web Case",
    "Operation Hydra Case",
    "Operation Wildfire Case",
    "Operation Bravo Case",
    "CS:GO Weapon Case",
    "CS:GO Weapon Case 2",
    "CS:GO Weapon Case 3",
    "eSports 2013 Case",
    "eSports 2013 Winter Case",
    "eSports 2014 Summer Case",
    # Cápsulas de Torneos Majors retiradas
    "Stockholm 2021 Contenders Sticker Capsule",
    "Stockholm 2021 Champions Autograph Capsule",
    "Antwerp 2022 Challengers Sticker Capsule",
    "Antwerp 2022 Legends Sticker Capsule",
    "Paris 2023 Contenders Sticker Capsule",
    "Paris 2023 Legends Sticker Capsule",
    "Paris 2023 Champions Autograph Capsule",
    "Copenhagen 2024 Challengers Sticker Capsule",
    "Copenhagen 2024 Contenders Sticker Capsule",
    "Copenhagen 2024 Champions Autograph Capsule"
}

def get_item_pool_status(item_name):
    """
    Determina la categoría de oferta y comportamiento macroeconómico del activo.
    Retorna un diccionario con detalles cuantitativos para el motor de riesgo.
    """
    for case in PRIME_ACTIVE_CASES:
        if case.lower() in item_name.lower():
            return {
                "category": "PRIME_ACTIVE",
                "label": "🟢 Drop Activo Semanal (~99%)",
                "supply_trend": "Alta inflación de oferta. Rotación rápida recomendada.",
                "recommended_horizon": "1 a 3 días (Swing rápido)",
                "supply_multiplier": 0.85, # Menor prima de retención
                "is_discontinued": False
            }

    for case in RARE_DROP_CASES:
        if case.lower() in item_name.lower():
            return {
                "category": "RARE_DROP",
                "label": "🟡 Rare Drop Pool (~0.5%)",
                "supply_trend": "Oferta en retroceso continuo. Alta probabilidad de apreciación.",
                "recommended_horizon": "2 a 8 semanas (Mediano Plazo)",
                "supply_multiplier": 1.15, # Mayor tolerancia a hold
                "is_discontinued": False
            }

    for item in DISCONTINUED_ASSETS:
        if item.lower() in item_name.lower():
            return {
                "category": "DISCONTINUED",
                "label": "🟣 Descontinuado / Retirado (0% Drop)",
                "supply_trend": "Oferta estrictamente fija o decreciente. Reserva de valor deflacionaria.",
                "recommended_horizon": "1 a 6 meses (Inversión Estructural)",
                "supply_multiplier": 1.30, # Máximo potencial de apreciación
                "is_discontinued": True
            }

    if "Sack of Gems" in item_name or "Gemas" in item_name:
        return {
            "category": "COMMODITY",
            "label": "💎 Materia Prima Líquida (Gemas)",
            "supply_trend": "Consumo continuo para crafteo de paquetes de cromos.",
            "recommended_horizon": "Intradía / Arbitraje Inmediato",
            "supply_multiplier": 1.0,
            "is_discontinued": False
        }

    # Si es skin o cromo normal
    return {
        "category": "REGULAR_MARKET",
        "label": "⚪ Mercado Regular",
        "supply_trend": "Sujeto a oferta y demanda estándar de jugadores.",
        "recommended_horizon": "1 a 7 días",
        "supply_multiplier": 1.0,
        "is_discontinued": False
    }
