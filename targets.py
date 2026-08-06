"""
Target universe and suppression list.

TARGETS is the ICP: companies building complex physical systems where test is the
bottleneck. Slug guesses are cheap because a 404 costs nothing; scan.py falls back
to reading the careers page when guessing fails.

SUPPRESSED is the list of publicly named customers and partners. These are removed
before ranking. Every entry cites where the relationship was disclosed, so the list
can be audited rather than trusted.
"""

TARGETS = {
    # aerospace / launch / hypersonics
    "Stoke Space":          ("Space / Launch",        ["stokespace", "stoke-space", "stoke"]),
    "Relativity Space":     ("Space / Launch",        ["relativity", "relativityspace"]),
    "Firefly Aerospace":    ("Space / Launch",        ["fireflyaerospace", "firefly"]),
    "Rocket Lab":           ("Space / Launch",        ["rocketlab", "rocketlabusa"]),
    "Ursa Major":           ("Space / Propulsion",    ["ursamajor", "ursamajortechnologies"]),
    "Venus Aerospace":      ("Hypersonics",           ["venusaero", "venusaerospace"]),
    "Impulse Space":        ("Space / Propulsion",    ["impulse", "impulsespace"]),
    "Astranis":             ("Space / Satellites",    ["astranis"]),
    "Apex":                 ("Space / Satellites",    ["apex-technology-inc", "apexspace"]),
    "K2 Space":             ("Space / Satellites",    ["k2space", "k2"]),
    "True Anomaly":         ("Space / Defense",       ["trueanomalyinc", "trueanomaly"]),
    "Varda Space":          ("Space / Manufacturing", ["vardaspace", "varda"]),
    "Vast Space":           ("Space Stations",        ["vast", "vastspace"]),
    "Sierra Space":         ("Space / Defense",       ["sierraspace"]),

    # defense / autonomy
    "Saronic":              ("Maritime Autonomy",     ["saronic"]),
    "Castelion":            ("Defense / Munitions",   ["castelion"]),
    "Epirus":               ("Defense / Directed E.", ["epirus"]),
    "Mach Industries":      ("Defense / Munitions",   ["mach", "machindustries"]),
    "Neros Technologies":   ("Defense / Drones",      ["nerostechnologies", "neros"]),
    "Skydio":               ("Drones / Autonomy",     ["skydio"]),
    "Applied Intuition":    ("Autonomy Software",     ["applied", "appliedintuition"]),
    "Forterra":             ("Ground Autonomy",       ["forterra", "forterrais"]),
    "Overland AI":          ("Ground Autonomy",       ["overlandai"]),
    "HavocAI":              ("Maritime Autonomy",     ["havocai"]),
    "Blue Water Autonomy":  ("Maritime Autonomy",     ["bluewaterautonomy"]),

    # advanced aviation
    "Joby Aviation":        ("eVTOL / Aviation",      ["joby", "jobyaviation"]),
    "Archer Aviation":      ("eVTOL / Aviation",      ["archer", "archeraviation"]),
    "Beta Technologies":    ("eVTOL / Aviation",      ["beta", "betatechnologies"]),
    "Electra":              ("Aviation",              ["electra", "electraaero"]),
    "Wisk Aero":            ("eVTOL / Aviation",      ["wisk", "wiskaero"]),

    # nuclear / fusion
    "Radiant Nuclear":      ("Nuclear",               ["radiant", "radiantnuclear"]),
    "Oklo":                 ("Nuclear",               ["oklo"]),
    "Kairos Power":         ("Nuclear",               ["kairospower"]),
    "X-energy":             ("Nuclear",               ["xenergy", "x-energy"]),
    "Commonwealth Fusion":  ("Fusion",                ["cfsenergy", "cfs"]),
    "Helion Energy":        ("Fusion",                ["helion", "helionenergy"]),
    "Zap Energy":           ("Fusion",                ["zapenergy"]),
    "Type One Energy":      ("Fusion",                ["typeoneenergy"]),
    "TAE Technologies":     ("Fusion",                ["tae", "taetechnologies"]),

    # robotics / industrial
    "Figure AI":            ("Humanoid Robotics",     ["figureai", "figure"]),
    "Agility Robotics":     ("Humanoid Robotics",     ["agilityrobotics"]),
    "Apptronik":            ("Humanoid Robotics",     ["apptronik"]),
    "Boston Dynamics":      ("Robotics",              ["bostondynamics"]),
    "Hadrian":              ("Precision Mfg",         ["hadrian-automation", "hadrian"]),
    "Divergent":            ("Advanced Mfg",          ["divergent", "divergent3d"]),

    # ground autonomy / AV
    "Zoox":                 ("Autonomous Vehicles",   ["zoox"]),
    "Nuro":                 ("Autonomous Vehicles",   ["nuro"]),
    "Kodiak Robotics":      ("Autonomous Trucking",   ["kodiak", "kodiakrobotics"]),
    "Torc Robotics":        ("Autonomous Trucking",   ["torcrobotics", "torc"]),
    "Gatik":                ("Autonomous Trucking",   ["gatik", "gatikai"]),
    "Plus":                 ("Autonomous Trucking",   ["plusai", "plus"]),
}

# Careers pages to scrape for a board token when slug guessing fails.
CAREERS = {
    "Joby Aviation":       ["https://www.jobyaviation.com/careers/"],
    "Beta Technologies":   ["https://www.beta.team/careers/"],
    "Commonwealth Fusion": ["https://cfs.energy/careers/open-positions"],
    "Boston Dynamics":     ["https://bostondynamics.com/careers/"],
    "Stoke Space":         ["https://www.stokespace.com/careers/"],
    "Firefly Aerospace":   ["https://fireflyspace.com/careers/"],
    "Castelion":           ["https://www.castelion.com/careers"],
    "Applied Intuition":   ["https://www.appliedintuition.com/careers"],
    "Forterra":            ["https://forterrais.com/careers/"],
    "Sierra Space":        ["https://www.sierraspace.com/careers/"],
    "Apex":                ["https://www.apexspace.com/careers"],
    "K2 Space":            ["https://www.k2space.com/careers"],
    "True Anomaly":        ["https://www.trueanomaly.space/careers"],
    "Overland AI":         ["https://www.overland.ai/careers"],
    "Blue Water Autonomy": ["https://www.bluewaterautonomy.com/careers"],
    "Electra":             ["https://www.electra.aero/careers"],
    "Wisk Aero":           ["https://wisk.aero/careers"],
    "X-energy":            ["https://x-energy.com/careers"],
    "Zap Energy":          ["https://www.zapenergy.com/careers"],
    "Type One Energy":     ["https://www.typeoneenergy.com/careers"],
    "TAE Technologies":    ["https://tae.com/careers/"],
    "Gatik":               ["https://gatik.ai/careers"],
    "Plus":                ["https://www.plus.ai/careers"],
    "Hadrian":             ["https://www.hadrian.co/careers"],
}

# Removed before ranking. Pitching a current customer is the fastest way for an
# internal GTM system to lose the sales team's trust.
SUPPRESSED = {
    "Varda Space":     "named customer (Contrary Research report)",
    "Radiant Nuclear": "named customer (Contrary Research report)",
    "Anduril":         "named customer (nominal.io)",
    "Shield AI":       "named customer (nominal.io)",
    "Hermeus":         "named customer (nominal.io)",
    "REGENT":          "named customer (nominal.io)",
    "Pratt Miller":    "named customer (nominal.io)",
    "Vatn Systems":    "named customer (Contrary Research report)",
    "Forterra":        "announced partner (Tectonic Defense)",
}
