from openerp import models, fields, api

class dym_report_request_tracking(models.Model):
    _inherit = 'account.voucher'
    
    # override list in custom module to add/drop columns
    # or change order of the partner summary table
    def _report_xls_request_tracking_fields(self, cr, uid, context=None):
        return [
            'no',\
            'date',\
            'branch_id',\
            'division',\
            'number',\
            'state_par',\
            'par_type',\
            'partner_code',\
            'partner_name',\
            'create_by',\
            'approved_by',\
            'approved_date',\
            'date_due',\
            'nama_account', \
            'description', \
            'a_code', \
            'a_name', \
            'aa_combi', \
            'aa_company', \
            'aa_bisnisunit', \
            'aa_branch', \
            'aa_costcenter', \
            'total',\
            'net_total',\
            # 'spa_number',\
            'spa_name',\
            'spa_amount',\
            'spa_method',\
            # 'payment_ref',\
            # 'settlement_name',\
            'nomor_giro',\
            'nomor_cba',\
            'no_bta', \
            'date_bta', \
            'state_bta', \
            'no_btr', \
            'date_btr', \
            'state_btr', \
            'no_withdrawal', \
            'date_withdrawal', \
            'state_withdrawal', \
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
     