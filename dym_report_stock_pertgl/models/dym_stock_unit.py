from openerp import models, fields, api


class dym_stock_unit_pertgl(models.Model):
    _inherit = 'stock.quant'
    
    
    def _report_xls_stock_unit_pertgl_fields(self, cr, uid, context=None):
        return [
            'cabang',
            'kode_product',
            'default_code',
            'color',
            'engine',
            'chassis',
            'umur',
            'tahun',
            'intransit',
            'rfs',
            'nrfs',
            'reserved',
            'undelivered',
            'location_id',
        ]
        
        
    def _report_xls_stock_sparepart_pertgl_fields(self, cr, uid, context=None):
        return [
            'branch_name',\
            'product_name',\
            'product_desc',\
            'ranking',\
            'parent_category',\
            'categ_parent_name',\
            'categ_name',\
            'total_stock',\
            'intransit',
            'rfs',
            'nrfs',
            'reserved',
            'undelivered',
            'location_parent',\
            'location_name',\
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
                'header': [1, 20, 'text', _('Partner ID')],
                'lines': [1, 0, 'text', _render("p['p_id']")],
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
                'header': [1, 20, 'text', _('Partner ID')],
                'lines': [1, 0, 'text', _render("p['p_id']")],
                'totals': [1, 0, 'text', None]},
        }
        return my_change
        """
        return {}
    