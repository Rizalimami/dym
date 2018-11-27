import time
from openerp.osv import orm, fields
import logging
_logger = logging.getLogger(__name__)
from lxml import etree

class back_to_rfs_info_wizard(orm.TransientModel):
    _name = 'back.to.rfs.info'

    _columns = {
        'retur_id': fields.many2one('dym.retur.jual', string='Return Jual'),
        'line_ids': fields.one2many('back.to.rfs.info.line', 'header_id', 'Line'),
        'state': fields.char(string='State', default='ok'),
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(back_to_rfs_info_wizard, self).default_get(cr, uid, fields, context=context)
        active_ids = context.get('active_ids', [])
        active_id = context.get('active_id', False)
        active_model = context.get('active_model')
        line_ids = []
        retur = self.pool.get(active_model).browse(cr, uid, active_ids, context=context)[0]
        for line in retur.retur_jual_line:
            if line.lot_state == 'stock':
                continue
            line_ids.append([0,0,{
                'product_id': line.product_id.id,
                'lot_id': line.lot_id.id,
                'lot_state': line.lot_id.state,
            }])
        if not line_ids:
            res['state'] = 'no_lines'
        res['retur_id'] = active_id
        res['line_ids'] = line_ids
        return res

    def action_oke(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids, context=context)
        if this.state == 'ok':
            for this_line in this.line_ids:
                for retur_line in this.retur_id.retur_jual_line:
                    if this_line.lot_id == retur_line.lot_id:
                        retur_line.lot_state = 'stock'
                        this.retur_id.lot_state = 'stock'
                        for quant in this_line.lot_id.quant_ids:
                            quant.reservation_id = False


class back_to_rfs_info_line_wizard(orm.TransientModel):
    _name = 'back.to.rfs.info.line'

    _columns = {
        'header_id': fields.many2one('back.to.rfs.info', string='Header'),
        'product_id': fields.many2one('product.product', string='Product'),
        'product_tmpl_id': fields.related('product_id', 'product_tmpl_id', relation='product.template', type='many2one', string='Product Template'),
        'lot_id': fields.many2one('stock.production.lot', string='Engine Number'),
        'lot_state': fields.char(string='Status'),
    }
