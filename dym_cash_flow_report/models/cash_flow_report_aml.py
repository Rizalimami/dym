from openerp import models, fields, api

class dym_report_cash_flow_account_move_line(models.Model):
    _inherit = 'account.move.line'
    
    # override list in custom module to add/drop columns
    # or change order of the partner summary table
    def _report_xls_cash_flow_fields(self, cr, uid, columns_add = [], context=None):
        return [
            'no',\
            'cabang',\
            'division',\
            'partner_code',\
            'partner_name',\
            'account_type',\
            'account_code',\
            'account_sap',\
            'invoice_name',\
            'name',\
            'date_aml',\
            'due_date',\
            'overdue',\
            'status',\
            'tot_invoice',\
            'amount_residual',\
            'current',\
            'reference',\
            'journal_name',
            'first_date',\
            'last_date',\
            'id_aml'
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
     