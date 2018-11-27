import time

import openerp
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import api, models
from datetime import datetime, date
from lxml import etree

class dym_stock_production_lot(osv.osv):
    _inherit = 'stock.production.lot'

    def get_location_before(self, cr, uid, ids, lot_id, context=None):
        for rec in self.browse(cr, uid, [lot_id], context=context):
            quant_obj = self.pool.get("stock.quant")
            quants = quant_obj.search(cr, uid, [('lot_id', 'in', [rec.id])], context=context)
            moves = []
            for quant in quant_obj.browse(cr, uid, quants, context=context):
                for move in quant.history_ids:
                    moves.append(move.id)
            if moves:
                obj_move_ids = self.pool.get('stock.move').search(cr, uid, [('id', 'in', moves)], order='date desc, id desc', context=context)
                obj_move = self.pool.get('stock.move').browse(cr, uid, obj_move_ids, context=context)
                flag = False
                branch_id = rec.branch_id.id
                for stock_move in obj_move:
                    if flag == True:
                        if stock_move.location_dest_id.id and stock_move.location_dest_id.usage == 'internal' and stock_move.location_dest_id.branch_id.id != branch_id:
                            return stock_move.location_dest_id.location_id.name + '/' + stock_move.location_dest_id.name                       
                    if stock_move.location_id.id and stock_move.location_id.usage == 'internal' and stock_move.location_id.branch_id.id != branch_id:
                        return  stock_move.location_id.location_id.name + '/' + stock_move.location_id.name
                    flag = True
            else:
                return '-'
        return '-'

class dym_barang_pindahan_report(osv.osv_memory):

    _name = 'dym.barang.pindahan.report'
    _description = 'Laporan Barang Pindahan'

    def _get_categ_ids(self, cr, uid, context=None):
        obj_categ = self.pool.get('product.category')
        all_categ_ids = obj_categ.search(cr, uid, [])
        categ_ids = obj_categ.get_child_ids(cr, uid, all_categ_ids, 'Unit')
        return categ_ids

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(dym_barang_pindahan_report, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        categ_ids = self._get_categ_ids(cr, uid, context)
        
        doc = etree.XML(res['arch'])
        nodes_product = doc.xpath("//field[@name='product_ids']")
        
        for node in nodes_product :
            node.set('domain', '[("categ_id", "in", '+ str(categ_ids)+')]')
        
        res['arch'] = etree.tostring(doc)
        return res

    _columns = {
        'branch_id': fields.many2one('dym.branch', 'Branch', required=True),
        'product_ids': fields.many2many('product.product', 'dym_barang_pindahan_product_rel', 'dym_barang_pindahan_wizard_id',
            'product_id', 'Products'),
    }        

class abstract_barang_pindahan_report(models.AbstractModel):
    _name = 'report.dym_barang_pindahan_report.barang_pindahan_report_template'

    def render_html(self, cr, uid, ids, data=None, context=None):
        registry = openerp.registry(cr.dbname)
        branch_id = False
        company = ''
        domain = [('location_id.usage','=','internal'),('location_id','!=','location_before')]
        domain_state = []
        lots = {}
        check_wizard = registry.get('dym.barang.pindahan.report').read(cr, uid, ids, context=context)
        if check_wizard:
            data_wizard = check_wizard[0]
            if data_wizard['branch_id'] != False:
                domain.append(('branch_id', '=', data_wizard['branch_id'][0]))
                branch_id = data_wizard['branch_id'][1]
                company = registry.get('dym.branch').browse(cr, uid, [data_wizard['branch_id'][0]], context=context).company_id.name
            if data_wizard['product_ids']:
                domain.append(('product_id', 'in', data_wizard['product_ids']))
            lot_ids = registry.get('stock.production.lot').search(cr, uid, domain, order='product_id asc, name asc', context=None)
            lots = registry.get('stock.production.lot').browse(cr, uid, lot_ids, context=context)
            if not lots:
                raise osv.except_osv(('Perhatian !'), ("Data pindahan barang tidak ditemukan."))
        report_obj = self.pool['report']
        report = report_obj._get_report_from_name(cr, uid, 'dym_barang_pindahan_report.barang_pindahan_report_template')
        docargs = {'doc_ids': ids,'doc_model': report.model,'docs': data,'branch_id': branch_id,'lots': lots,'company':company}
        return report_obj.render(cr, uid, ids, 'dym_barang_pindahan_report.barang_pindahan_report_template', docargs, context=context)