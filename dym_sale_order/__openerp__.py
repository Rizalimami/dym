{
    "name":"Sales Memo Sparepart",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        Sales Memo Sparepart
    """,
    "depends":[
        "base", 
        "product", 
        "account", 
        "sale",
        "account_voucher", 
        "sale_stock",
        "dealer_sale_order", 
        "dym_branch", 
        "dym_serial_number", 
    ],
    "data":[
    	"report/report_cetakan_so.xml",
        "report/report_cetakan_so_kecil.xml",
        "report/report_kwitansi_kecil_so.xml",
        "report/report_nsc_so.xml",
        "views/dym_generate_df_view.xml",
        "views/dym_sale_order_report_view.xml",
        # "data/dym_branch_config.xml",
        "views/res_partner_view.xml",
        "views/dym_sale_order_view.xml",
        "views/dym_branch_config_view.xml",
        "views/dym_approval_so_view.xml",
        # "security/res_groups.xml",
        ],
    "active":False,
    "installable":True
}