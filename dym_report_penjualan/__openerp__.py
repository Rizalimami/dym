{
    "name":"Report Penjualan",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module",
    "description":"Report Penjualan",
    "depends":["base","dealer_sale_order"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
        "wizard/dym_report_penjualan_wizard.xml",
        # "security/res_groups.xml",
        "security/ir.model.access.csv",
        "report/dym_report_penjualan_in_report_view.xml",
    ],
    "active":False,
    "installable":True
}