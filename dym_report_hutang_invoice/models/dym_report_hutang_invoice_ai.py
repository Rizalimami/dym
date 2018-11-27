from openerp import models, fields, api

class dym_report_hutang_account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    # override list in custom module to add/drop columns
    # or change order of the partner summary table
    def _report_xls_hutang_invoice_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_status',\
            'branch_id',\
            'division',\
            # 'invoice_name',\
            'number',\
            'origin',\
            'type',\
            'date_ai',\
            'date_due',\
            'supplier_invoice_number',\
            'partner_code',\
            'partner_name',\
            'journal_name',\
            'account_code',\
            'account_name',\
            'analytic_combination',\
            'analytic_1',\
            'analytic_2',\
            'analytic_3',\
            'analytic_4',\
            'total',\
            'residual',\
            'state'
        ]
 
    # override list in custom module to add/drop columns
    # or change order of the partner summary table
    def _report_xls_arap_details_fields(self, cr, uid, context=None):
        return [
            'document', 'date', 'date_maturity', 'account', 'description',
            'rec_or_rec_part', 'debit', 'credit', 'balance',
            # 'partner_id',
        ]
 
    # Change/Add Template entries
    def _report_xls_arap_overview_template(self, cr, uid, context=None):
        """
        Template updates, e.g.
 
        my_change = {
            'partner_id':{
                'header': [1, 20, 'text', _('Move Line ID')],
                'lines': [1, 0, 'text', _render("p['ids_aml']")],
                'totals': [1, 0, 'text', None]},
        }
        return my_change
        """
        return {}
 
    # Change/Add Template entries
    def _report_xls_arap_details_template(self, cr, uid, context=None):
        """
        Template updates, e.g.
 
        my_change = {
            'partner_id':{
                'header': [1, 20, 'text', _('Move Line ID')],
                'lines': [1, 0, 'text', _render("p['ids_aml']")],
                'totals': [1, 0, 'text', None]},
        }
        return my_change
        """
        return {}
     