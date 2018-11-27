from openerp import models, fields, api

class dym_report_pembelianmesin_ai(models.Model):
    _inherit = 'account.invoice'
    
    def _report_xls_pembelianmesin_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_code',\
            'branch_name',\
            'document_date',\
            'supplier_invoice_number',\
            'supplier_code',\
            'supplier_name',\
            'date_invoice',\
            'inv_number',\
            'state',\
            'type',\
            'prod_desc',\
            'warna',\
            'prod_categ_name',\
          #  'qty',\
          #  'consolidated_qty',\
          #  'unconsolidated_qty',\
            'price_unit',\
            'total_sales',\
            'disc_amount',\
            'discount_cash_avg',\
            'discount_program_avg',\
            'discount_lain_avg',\
            'total_dpp',\
            'total_ppn',\
            'tgl_retur',\
            'no_retur',\
            'qty_retur',\
            'retur_total',\
            'total_hutang',\
            'purchase_date',\
            'purchase_name',\
            'tgl_grn',\
            'no_grn',\
            #'analytic_combination',\
            #'analytic_1',\
            #'analytic_2',\
            #'analytic_3',\
            #'analytic_4',\
            'account_code',\
            #'loan_name',\
            #'loan_date',\
            'engine_number',\
            # 'consolidate_status',\
            # 'branch_status',\
            # 'division',\
            # 'origin',\
            # 'discount',\
            # 'sales_per_unit',\
            # 'taxes',\
            'tgl_cin', \
            'no_cin', \
        ]
    