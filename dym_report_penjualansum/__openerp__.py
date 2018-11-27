{
    "name":"Report Penjualan Sum",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module",
    "description":"Report Penjualan Sum",
    "depends":[
        "base",
        "dealer_sale_order",
        "dym_report_penjualantax"
    ],
    "init_xml":[],
    "demo_xml":[],
    "data":[
        "security/ir.model.access.csv",
        "wizard/dym_report_penjualansum_wizard.xml",
        "report/dym_report_penjualansum_in_report_view.xml",
    ],
    "active":False,
    "installable":True
}