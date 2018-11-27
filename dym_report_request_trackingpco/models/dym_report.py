from openerp import models, fields, api

class dym_report_request_trackingpco(models.Model):
    _inherit = 'account.voucher'
    
    # override list in custom module to add/drop columns
    # or change order of the partner summary table
    def _report_xls_request_trackingpco_fields(self, cr, uid, context=None):
        return [
            'no',\
            'pco_date',\
            'cabang',\
            'division',\
            'pco_number',\
            'pco_state',\
            'pco_acc',\
            'pco_desc',\
            'pco_total',\
            'pco_anl_bu',\
            'pco_anl_br',\
            'pco_anl_cc',\
            'pci_number',\
            'jml_kasbon',\
            'receive_amount',\
            'pco_new_number',\
            'pco_new_state',\
            'pco_new_acc',\
            'pcol_new_desc',\
            'pco_new_total',\
            'pco_new_anl_bu',\
            'pco_new_anl_br',\
            'pco_new_anl_cc',\
            'reimbursed_number',\
            'reimbursed_request',\
            'reimbursed_approve',\
            'reimbursed_state',\
            'bta_name',\
            'bta_date',\
            'bta_state',\
            'dbt_name',\
            'dbt_date',\
            'dbt_state',\
            'withdraw_name',\
            'withdraw_date',\
            'withdraw_state',\
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
     