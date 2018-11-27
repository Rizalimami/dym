from openerp import models, fields, api

class dym_report_workshop(models.Model):
    _inherit = 'dym.work.order'
    
    def _report_xls_workshop_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_code',\
            'branch_name',\
            'wo_name',\
            'wo_state',\
            'wo_date',\
            'wo_type',\
            'main_dealer',\
            'login',\
            'mechanic',\
            'nopol',\
            'cust_code',\
            'cust_name',\
            'cust_mobile',\
            'unit_name',\
            'engine',\
            'chassis',\
            'wo_categ',\
            'prod_categ_name',\
            'prod_name',\
            'prod_code',\
            'qty',\
            'het',\
            'discount',\
            'hpp',\
            'dpp',\
            'ppn',\
            'total',\
            'total_gp',\
            'faktur_pajak',\
        ]
    