from openerp import models, fields, api

class dym_report_program_subsidi(models.Model):
    _inherit = 'dealer.sale.order.line.discount.line'
    
    # override list in custom module to add/drop columns
    # or change order of the partner summary table
    def _report_xls_program_subsidi_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_id',\
            'division',\
            'number',\
            'date',\
            'invoice_number',\
            'invoice_date',\
            'type',\
            'warna',\
            'engine_number',\
            'program',\
            'ps_md',\
            'ps_ahm',\
            'ps_finco',\
            'ps_dealer',\
            'ps_others',\
            'discount',\
            'disc_pelanggan',\
            'ps_md_real',\
            'ps_ahm_real',\
            'ps_finco_real',\
            'ps_dealer_real',\
            'ps_others_real',\
            'discount_real',\
            'disc_pelanggan_real'
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
     