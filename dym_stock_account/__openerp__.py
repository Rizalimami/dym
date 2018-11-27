{
    "name":"Stock Account",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description":"Stock Account",
    "depends":["base","dym_dealer_menu","stock","stock_account","dym_branch","dym_approval"],
    "data":[
            # "workflow/product_cost_adjustment_approval_workflow.xml",
            "views/product_cost_warehouse_view.xml",
            "views/branch_config_view.xml",
            "wizard/dym_cost_price_history_report_wizard_view.xml",
            "security/ir.model.access.csv",
            "data/ir_sequence.xml",
                  ],
    "active":False,
    "installable":True
}