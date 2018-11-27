{
    "name":"Stock Mutation",
    "version":"1.0",
    "author":"One-D",
    "category":"DAYA",
    "description":"Stock Mutation",
    "depends":[
        "base",
        "dym_branch",
        "dym_dealer_menu",
        "dym_approval",
        "dym_purchase_order"
    ],
    "data":[
        "views/dym_mutation_request_view.xml",
        "views/dym_stock_distribution_view.xml",
        "views/dym_mutation_order_view.xml",
        "views/dym_approval_stock_mutation_view.xml",
        "views/dym_approval_stock_distribution_view.xml",
        "views/dym_mutation_request_workflow.xml",
        # "dym_stock_distribution_workflow.xml",
        # "dym_mutation_order_workflow.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        # "security/res_groups.xml",
        # "security/res_groups_button.xml",
        "data/dym_approval_config_data.xml"
    ],
    "active":False,
    "installable":True
}