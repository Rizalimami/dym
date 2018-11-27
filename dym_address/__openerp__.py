{
    "name":"DYM Addresses",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        Master Province, City, Kecamatan, Keluarahan
    """,
    "depends":[
        "base",
        "dym_dealer_menu"
    ],
    "data":[
        "views/dym_city_view.xml",
        "views/dym_kecamatan_view.xml",
        "views/dym_kelurahan_view.xml",
        "security/ir.model.access.csv",
    ],
    "active":False,
    "installable":True
}