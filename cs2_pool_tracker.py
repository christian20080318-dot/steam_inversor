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

def parse_cs2_item_details(item_name, app_id=730):
    """
    Descompone el nombre de un activo de Steam en su traducción al español,
    tipo de objeto y estado de desgaste oficial en español de Valve.
    """
    wear_map = {
        "Factory New": {"es": "Recién fabricado", "short": "FN", "icon": "✨"},
        "Minimal Wear": {"es": "Casi nuevo", "short": "MW", "icon": "💎"},
        "Field-Tested": {"es": "Algo desgastado", "short": "FT", "icon": "🛡️"},
        "Well-Worn": {"es": "Bastante desgastado", "short": "WW", "icon": "⚠️"},
        "Battle-Scarred": {"es": "Deplorable", "short": "BS", "icon": "💀"}
    }

    detected_wear = None
    for en_wear, info in wear_map.items():
        if f"({en_wear})" in item_name or en_wear.lower() in item_name.lower():
            detected_wear = {
                "en": en_wear,
                "es": info["es"],
                "short": info["short"],
                "icon": info["icon"],
                "label": f"{info['icon']} *{info['es']}* ({en_wear} - {info['short']})"
            }
            break

    # Diccionario de traducción al español de skins populares
    skin_translations = {
        "Army Sheen": "Brillo Militar",
        "Slate": "Pizarra",
        "Phantom Disruptor": "Disruptor Fantasma",
        "Elite Build": "Construcción de Élite",
        "Atheris": "Atheris",
        "Mortis": "Mortis",
        "Duality": "Dualidad",
        "Cortex": "Corteza",
        "Cyrex": "Cyrex",
        "Evil Daimyo": "Daimyo Malvado",
        "Night Terror": "Terror Nocturno",
        "Decimator": "Diezmador",
        "Mecha Industries": "Industrias Mecha",
        "Trigger Discipline": "Disciplina de Gatillo",
        "Water Elemental": "Elemental de Agua",
        "Vogue": "Moda (Vogue)",
        "Sand Dune": "Duna de Arena",
        "Predator": "Depredador",
        "Sand Spray": "Ráfaga de Arena"
    }

    item_type = "Activo de Mercado"
    if "Case" in item_name or "Caja" in item_name:
        item_type = "📦 Caja de Armas CS2"
    elif "Sticker Capsule" in item_name or "Cápsula" in item_name:
        item_type = "🏆 Cápsula de Pegatinas Major"
    elif "Sealed Graffiti" in item_name or "Graffiti" in item_name:
        item_type = "🎨 Graffiti Sellado CS2"
    elif any(r in item_name for r in ["AK-47", "M4A4", "M4A1-S", "SG 553", "Galil", "AUG", "FAMAS"]):
        item_type = "🔫 Rifle de Asalto CS2"
    elif any(r in item_name for r in ["AWP", "SSG 08", "SCAR-20", "G3SG1"]):
        item_type = "🎯 Rifle de Francotirador CS2"
    elif any(r in item_name for r in ["USP-S", "Glock-18", "Desert Eagle", "P250", "Five-SeVeN", "Tec-9", "P2000", "Dual Berettas", "CZ75"]):
        item_type = "🔫 Pistola CS2"
    elif any(r in item_name for r in ["P90", "MP9", "MAC-10", "MP7", "UMP-45", "MP5"]):
        item_type = "⚡ Subfusil CS2"
    elif any(r in item_name for r in ["Nova", "XM1014", "MAG-7", "Sawed-Off", "M249", "Negev"]):
        item_type = "💥 Escopeta / Pesada CS2"
    elif "Mann Co." in item_name or "Key" in item_name:
        item_type = "🔑 Llave TF2 (Divisa Líquida)"
    elif "Ticket" in item_name:
        item_type = "🎫 Billete de Misión TF2"
    elif "Sack of Gems" in item_name:
        item_type = "💎 Materia Prima (Saco de Gemas)"
    elif app_id == 753 or "-" in item_name:
        item_type = "🃏 Cromo Coleccionable de Steam"

    friendly_name = item_name
    for en_skin, es_skin in skin_translations.items():
        if en_skin != es_skin and en_skin in friendly_name and f"({es_skin})" not in friendly_name:
            friendly_name = friendly_name.replace(en_skin, f"{en_skin} ({es_skin})")
            break

    return {
        "original_name": item_name,
        "friendly_name": friendly_name,
        "item_type": item_type,
        "wear": detected_wear
    }
