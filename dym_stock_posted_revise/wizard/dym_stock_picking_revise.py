import time

from openerp.osv import fields, osv
from openerp.tools.translate import _
from lxml import etree

class dym_stock_packing_revise_line(osv.osv_memory):
    _name = "dym.stock.packing.revise.line"
    _description = "Stock Picking Revise Line"

    _columns = {
        'template_ids': fields.char(string='Type'),
        'dym_packing_id': fields.many2one('dym.stock.packing', 'Picking'),
        'packing_revise_id': fields.many2one('dym.stock.packing.revise', 'Packing Revise'),
        'lot_id': fields.many2one('stock.production.lot', string="Lot"),
        'template_id': fields.many2one('product.template', string="Type"),
        'template_id_new': fields.many2one('product.template', string="New Type"),
        'product_id': fields.many2one('product.product', string="Warna"),
        'product_id_new': fields.many2one('product.product', string="New Warna"),
        'engine_number': fields.char(string='Engine No'),
        'chassis_number': fields.char(string='Chassis No'),
        'tahun_pembuatan': fields.char(string='Thn Pembuatan', size=4),
        'engine_number_new': fields.char(string='New Engine No'),
        'chassis_number_new': fields.char(string='New Chassis No'),
        'tahun_pembuatan_new': fields.char(string='New Thn Pembuatan', size=4),
    }

    def onchange_engine_number(self, cr, uid, ids, engine_number, engine_number_new, chassis_number, chassis_number_new, tahun_pembuatan, tahun_pembuatan_new, context=None):
        if engine_number_new and engine_number!=engine_number_new:
            pass

    def onchange_template_id_new(self, cr, uid, ids, packing_id, template_id, product_id, engine_number, engine_number_new, chassis_number, chassis_number_new, tahun_pembuatan, tahun_pembuatan_new, context=None):
        res = {}
        value = {}
        domain = {}

        packing_id = self.pool.get('dym.stock.packing').browse(cr, uid, [packing_id], context=context)[0]
        origin = packing_id.rel_origin
        origin_id = self.pool.get('purchase.order').search(cr, uid, [('name','=',origin)], context=context)
        if not origin_id:
            raise osv.except_osv(_('Warning!'),
            _('Purchase Order "%s" tidak ditemukan.' % origin))
        po = self.pool.get('purchase.order').browse(cr, uid, origin_id, context=context)
        po_prod_tmpl_ids = [p.template_id.id for p in po.order_line]
        po_prod_ids = [p.product_id.id for p in po.order_line]
        if template_id not in po_prod_tmpl_ids:
            prod_template = self.pool.get('product.template').browse(cr, uid, [template_id], context=context)[0]
            value['template_id_new'] = False
            raise osv.except_osv(_('Warning!'),
            _('Type product "%s" tidak ditemukan pada PO nomor %s.' % (prod_template.name,origin)))
        categ_ids = self.pool.get('product.category').search(cr, uid, [('id','child_of','Unit')], context=context)
        product_ids = self.pool.get('product.product').search(cr, uid, [('product_tmpl_id','=',template_id)], context=context)
        domain['template_id_new'] = [('categ_id','in',categ_ids),('id','in',po_prod_tmpl_ids)]
        domain['product_id_new'] = [('id','in',product_ids),('id','in',po_prod_ids)]

        res['value'] = value
        res['domain'] = domain
        return res

    def onchange_product_id(self, cr, uid, ids, template_id, product_id, engine_number, engine_number_new, chassis_number, chassis_number_new, tahun_pembuatan, tahun_pembuatan_new, context=None):
        pass

class dym_stock_packing_revise(osv.osv_memory):
    _name = "dym.stock.packing.revise"
    _description = "Stock Picking Revise"

    _columns = {
        'dym_packing_id': fields.many2one('dym.stock.packing', 'Picking'),
        'dym_packing_revise_line': fields.one2many('dym.stock.packing.revise.line', 'packing_revise_id', string='Lines'),
        'sj_date': fields.date(string='Tanggal Surat Jalan'),
        'sj_date_new': fields.date(string='New Tgl SJ'),
        'sj_no': fields.char(string='Nomor Surat Jalan'),
        'sj_no_new': fields.char(string='New Nomor SJ'),
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}

        res = super(dym_stock_packing_revise, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)
        if context.get('active_model','') == 'stock.stock.packing' and len(context['active_ids']) < 2:
            raise osv.except_osv(_('Warning!'),
            _('Please select multiple shipments to revise in the list view.'))
        this = self.pool.get(context.get('active_model')).browse(cr, uid, [context['active_id']], context=context)
        origin = this.rel_origin
        origin_id = self.pool.get('purchase.order').search(cr, uid, [('name','=',origin)], context=context)
        if not origin_id:
            raise osv.except_osv(_('Warning!'),
            _('Purchase Order "%s" tidak ditemukan.' % origin))

        po = self.pool.get('purchase.order').browse(cr, uid, origin_id, context=context)
        po_prod_ids = [p.template_id.id for p in po.order_line]
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='dym_packing_revise_line']/tree/field[@name='template_id_new']")
        for node in nodes_branch :
            node.set('domain', "[('id','in',"+str(po_prod_ids)+"))]")
        res['arch'] = etree.tostring(doc)
        return res

    def default_get(self, cr, uid, fields, context=None):
        res = super(dym_stock_packing_revise, self).default_get(
            cr, uid, fields, context=context)
        active_model = context.get('active_model',False)
        active_ids = context.get('active_ids',False)
        active_id = context.get('active_id',False)
        if not all([active_model,active_model=='dym.stock.packing',active_id]):
            return res
        res['dym_packing_id'] = active_id
        data = self.pool.get('dym.stock.packing').browse(cr, uid, active_ids, context=context)
        dym_packing_revise_lines = []

        origin = data.rel_origin
        origin_id = self.pool.get('purchase.order').search(cr, uid, [('name','=',origin)], context=context)
        po = self.pool.get('purchase.order').browse(cr, uid, origin_id, context=context)
        po_prod_ids = [p.template_id.id for p in po.order_line]

        for line in data.packing_line:
            lot_id = self.pool.get('stock.production.lot').search(cr, uid, [('name','=',line.engine_number)], context=context)
            if not lot_id:
                continue
            dym_packing_revise_lines.append((0,0,{
                'template_ids': po_prod_ids,
                'lot_id': lot_id[0],
                'dym_packing_id': active_id,
                'engine_number': line.engine_number,
                'chassis_number': line.chassis_number,
                'tahun_pembuatan': line.tahun_pembuatan,
                'template_id': line.template_id.id,
                'product_id': line.product_id.id,
            }))
        res.update({
            'sj_no': data.sj_no,
            'sj_date': data.sj_date,
            'dym_packing_revise_line': dym_packing_revise_lines,
        })        
        return res

    def revise_shipments(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids, context=context)
        packing_id = this.dym_packing_id
        origin = packing_id.rel_origin
        origin_id = self.pool.get('purchase.order').search(cr, uid, [('name','=',origin)], context=context)
        for data in self.browse(cr, uid, ids, context=context):
            vals = {}
            if data.sj_date_new and data.sj_date != data.sj_date_new:
                vals['sj_date'] = data.sj_date_new
            if data.sj_no_new and data.sj_no != data.sj_no_new:
                vals['sj_no'] = data.sj_no_new
            if vals:
                data.dym_packing_id.write(vals)
            for line in data.dym_packing_revise_line:
                packing_vals = {}
                lot_vals = {}
                if line.template_id_new and line.template_id != line.template_id_new:
                    packing_vals['template_id'] = line.template_id_new.id
                if line.product_id_new and line.product_id != line.product_id_new:
                    packing_vals['product_id'] = line.product_id_new.id
                    lot_vals['product_id'] = line.product_id_new.id
                if line.engine_number_new and line.engine_number != line.engine_number_new:
                    packing_vals['engine_number'] = line.engine_number_new
                    lot_vals['name'] = line.engine_number_new
                if line.chassis_number_new and line.chassis_number != line.chassis_number_new:
                    packing_vals['chassis_number'] = line.chassis_number_new
                    lot_vals['chassis_no'] = line.chassis_number_new
                if line.tahun_pembuatan_new and line.tahun_pembuatan != line.tahun_pembuatan_new:
                    packing_vals['tahun_pembuatan'] = line.tahun_pembuatan_new
                    lot_vals['tahun'] = line.tahun_pembuatan_new
                packing_line = data.dym_packing_id.packing_line.filtered(lambda s: s.engine_number == line.engine_number)
                if packing_vals:
                    packing_line.write(packing_vals)
                if lot_vals:
                    line.lot_id.write(lot_vals)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
