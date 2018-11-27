{
    "name":"Report Penjualan Acc",
    "version":"1.0",
    "author":"Yordan",
    "category":"Custom Module",
    "description":"Report Penjualan Acc",
    "depends":[
        "base",
        "dealer_sale_order",
        "dym_report_penjualantax",
    ],
    "init_xml":[],
    "demo_xml":[],
    "data":[
        "security/ir.model.access.csv",
        "wizard/dym_report_penjualanacc_wizard.xml",
        "report/dym_report_penjualanacc_in_report_view.xml",
    ],
    "active":False,
    "installable":True
}