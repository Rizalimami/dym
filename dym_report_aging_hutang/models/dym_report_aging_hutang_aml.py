from openerp import models, fields, api

class dym_report_aging_hutang_account_move_line(models.Model):
    _inherit = 'account.move.line'
    
    # override list in custom module to add/drop columns
    # or change order of the partner summary table
    def _report_xls_aging_hutang_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_code',\
            'branch_name',\
            'date_aml',\
            'invoice_name',\
            'partner_code',\
            'partner_name',\
            'supplier_invoice_date',\
            'supplier_invoice_number',\
            # 'acc_number',\
            # 'bank',\
            # 'an_rek',\
            # 'tgl_retur',\
            # 'no_retur',\
            # 'total_retur',\
            # 'status',\
            'due_date',\
            'payment_term',\
            'tot_invoice',\
            # 'amount_residual',\
            'overdue',\
            'belum_jatuh_tempo',\
            'overdue_1_30',\
            'overdue_31_60',\
            'overdue_61_90',\
            'overdue_91_n',\
            # 'account_code',\
            # 'analytic_combination',\
            # 'analytic_1',\
            # 'analytic_2',\
            # 'analytic_3',\
            # 'analytic_4',\
            # 'branch_status',\
            # 'branch_name',\
            # 'division',\
            # 'name',\
            # 'reference',\
            # 'journal_name',
        ]

    def _report_xls_aging_hutang_fields_detail_pembayaran(self, cr, uid, context=None):
        return [
            'no',\
            'date_aml',\
            'invoice_name',\
            'supplier_invoice_date',\
            'supplier_invoice_number',\
            'partner_code',\
            'partner_name',\
            'acc_number',\
            'bank',\
            'an_rek',\
            # 'tgl_retur',\
            # 'no_retur',\
            # 'total_retur',\
            'status',\
            'due_date',\
            'tot_invoice',\
            'pay_date',\
            'pay_no',\
            # 'pay_retur',\
            'pay_pindahan',\
            'pay_amount',\
            'amount_residual',\
            'belum_jatuh_tempo',\
            'overdue',\
            'overdue_1_30',\
            'overdue_31_60',\
            'overdue_61_90',\
            'overdue_91_n',\
            'account_code',\
            'analytic_combination',\
            'analytic_1',\
            'analytic_2',\
            'analytic_3',\
            'analytic_4',\
            # 'branch_status',\
            # 'branch_name',\
            # 'division',\
            # 'name',\
            # 'reference',\
            # 'journal_name',
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
     