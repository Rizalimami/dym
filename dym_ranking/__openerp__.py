{
    "name":"Analisa Ranking & Order Suggestion",
    "version":"0.1",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        
    """,
    "depends":[
        "base", 
        "dym_branch", 
        "dym_dealer_menu",
        "dym_pricelist"
    ],
    "data":[
        "views/ranking.xml",
        "views/dym_pricelist.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml", 
    ],
    "active":False,
    "installable":True
}
