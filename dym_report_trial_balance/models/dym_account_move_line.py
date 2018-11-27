from openerp import models, fields, api

class dym_account_move_line(models.Model):
    _inherit = 'account.move.line'

    def _report_xls_trial_balance_fields(self, cr, uid, context=None):
        return [
            'no',\
            'account_code',\
            'branch_status',\
            'branch_name',\
            # 'account_sap',\
            'account_name',\
            'account_type',\
            'analytic_combination',\
            'analytic_1',\
            'analytic_2',\
            'analytic_3',\
            'analytic_4',\
            'saldo_awal_debit',\
            'saldo_awal_credit',\
            'mutasi_debit',\
            'mutasi_credit',\
            'debit_neraca',\
            'credit_neraca',\
            'net',\
        ]

    def _report_xls_trial_balance_fields_consol(self, cr, uid, context=None):
        return [
            'no',\
            'account_code',\
            'branch_status',\
            'branch_name',\
            # 'account_sap',\
            'account_name',\
            'account_type',\
            'analytic_combination',\
            'analytic_1',\
            'analytic_2',\
            'analytic_3',\
            'analytic_4',\
            'saldo_awal_debit',\
            'saldo_awal_credit',\
            'mutasi_debit',\
            'mutasi_credit',\
            'debit_neraca',\
            'credit_neraca',\
            'net',\
            'elim_debit',\
            'elim_credit',\
            'consol_debit',\
            'consol_credit',\
            'consol_net',\
        ]

    def _report_xls_trial_balance_import_sun_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_code',\
            'account_code',\
            'account',\
            'analytic_1',\
            'analytic_2',\
            'analytic_3',\
            'analytic_4',\
            'profit_centre',\
            'div',\
            'dept',\
            'class',\
            'type',\
            'account_name',\
            'transaction_amount',\
            'date_stop',\
            'trans_reference',\
            'memo_amount',\
            'debit',\
            'credit',\

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
                'lines': [1, 0, 'text', _render("p['id_aml']")],
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
                'lines': [1, 0, 'text', _render("p['id_aml']")],
                'totals': [1, 0, 'text', None]},
        }
        return my_change
        """
        return {}
     