from openerp import models, fields, api


class dym_stock_unit(models.Model):
    _inherit = 'stock.quant'
    
    
    def _report_xls_stock_unit_fields(self, cr, uid, context=None):
        return [
            'cabang',
            'code',
            'p_categ_name' ,
            'kode_product',
            'default_code',
            'color',
            'location_id',
            'tanggal',
            'grn_no',
            'engine',
            'chassis',
            'tahun',
            'jumlah',
            # 'nilai',
            'state_stock',
            'state',
            'umur',
            'umur_mutasi',
            'origin',
            'branch_source'
            # 'partner_id'
        ]
        
        
    def _report_xls_stock_sparepart_fields(self, cr, uid, context=None):
        return [
            'branch_id',\
            'branch_code',\
            'branch_name',\
            'pack_name',\
            'pack_date',\
            'parent_category',\
            'categ_parent_name',\
            'category_id',\
            'categ_name',\
            'product_name_tmpl_id',\
            'product_name',\
            'p_product_id',\
            'default_code',\
            'ranking',\
            'location_parent',\
            'location_name',\
            'loc_id',\
            'status',\
            'quantity'
            # 'move_origin',\
            # 'picking_name',\
            # 'harga_satuan',\
            # 'total_harga'
            # 'product_desc',\
            # 'aging',\
        ]
        
    
    def _report_xls_stock_extras_fields(self, cr, uid, context=None):
        return [
            'branch_code',\
            'branch_name',\
            'parent_category',\
            'product_desc',\
            'default_code',
            'categ_name',\
            'product_name',\
            'move_origin',\
            'picking_name',\
            'unit_grn',\
            'location_parent',\
            'location_name',\
            'status',\
            # 'aging',\
            'quantity',\
            'harga_satuan',\
            'total_harga'
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
    