{
    "name":"Report Penjualan Tax",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module",
    "description":"Report Penjualan Tax",
    "depends":[
        "base",
        "dealer_sale_order",
        "dym_proposal_event",
    ],
    "init_xml":[],
    "demo_xml":[],
    "data":[
        "security/ir.model.access.csv",
        "wizard/dym_report_penjualantax_wizard.xml",
        "report/dym_report_penjualantax_in_report_view.xml",
    ],
    "active":False,
    "installable":True
}