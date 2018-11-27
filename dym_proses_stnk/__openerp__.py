{
    "name":"Proses STNK",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        Permohonan Faktur
    """,
    "depends":[
        "base",
        "account",
        "dym_branch",
        "stock",
        "dym_dealer_menu",
        "dym_serial_number",
        "dym_approval"
    ],
    "data":[            
        "report/report_penerimaan_bpkb.xml",
        "report/report_penerimaan_stnk.xml",
        "report/report_proses_stnk.xml",
        "report/proses_stnk_report.xml",
        "report/report_proses_birojasa.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml", 
        "data/dym_approval_config_data.xml",         
        "views/dym_proses_stnk_report.xml",
        "views/dym_proses_birojasa_workflow.xml",                              
        "views/dym_approval_proses_birojasa_workflow.xml",
        "views/dym_lokasi_bpkb_view.xml",
        "views/dym_lokasi_stnk_view.xml",
        "views/dym_proses_stnk_view.xml",
        "views/dym_penerimaan_stnk_view.xml",
        "views/dym_penerimaan_bpkb_view.xml",
        "views/dym_proses_birojasa_view.xml",
        "views/dym_approval_proses_birojasa_view.xml",
        "views/dym_mutasi_bpkb_view.xml",
        "views/dym_mutasi_stnk_view.xml",
        "views/dym_serial_number_pf_view.xml",
        "views/dym_branch_config_view.xml",
        "views/dym_birojasa_withholding_tax_view.xml",
        "views/dym_account_invoice_withholding_tax_view.xml",
        "views/dym_batal_birojasa.xml",
        "views/dym_batal_birojasa_workflow.xml",
        "wizard/wiz_dym_batal_birojasa.xml",
        # "security/res_groups.xml",                
        # "security/res_groups_button.xml",
        # "data/dym.branch.config.xml",
        # "data/ir.sequence.xml"    
    ],
    "active":False,
    "installable":True
}