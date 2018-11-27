{
    "name":"Pricelist",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description":"Pricelist",
    "depends":[
        "base",
        "product",
        "dym_branch"
    ],
    "data":[
        "views/dym_pricelist_view.xml",            
        "security/ir.model.access.csv",
        # "security/res_groups.xml",
    ],
    "active":False,
    "installable":True
}