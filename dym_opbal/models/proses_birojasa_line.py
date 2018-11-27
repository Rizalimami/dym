# -*- coding: utf-8 -*-
import time
from datetime import datetime
from openerp import workflow
from openerp.osv import fields, osv, orm
import openerp.addons.decimal_precision as dp
from openerp import netsvc
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval
from lxml import etree
from openerp.osv.orm import setup_modifiers

class dym_proses_birojasa_line(osv.osv):
    _inherit = "dym.proses.birojasa.line"

    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        res={}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = {
                'koreksi': 0.0,
                'titipan': 0.0,
                'margin': 0.0,
            }
            koreksi = (line.total_tagihan or 0.0) -  (line.total_estimasi or 0.0) -  (line.pajak_progressive or 0.0)
            if line.is_opbal:
                opbal_obj = self.pool.get('opbal.customer.deposit')
                titipan_stnk_id = opbal_obj.search(cr, uid, [('engine_id','=',line.name.id)], context=context)
                if not titipan_stnk_id:
                    return res
                titipan_stnk = opbal_obj.browse(cr, uid, titipan_stnk_id, context=context)
                titipan = titipan_stnk.amount or 0.0
                if not titipan:
                    return res
            else:
                mod_obj = self.pool.get('dealer.sale.order.line')
                if mod_obj:
                    obj_ids = mod_obj.search(cr, uid, [('dealer_sale_order_line_id','=',line.name.dealer_sale_order_id.id),('lot_id','=',line.name.id)], limit=1)
                    if not obj_ids:
                        mod_obj = self.pool.get('dym.retur.jual.line')
                        obj_ids = mod_obj.search(cr, uid, [('dso_line_id.dealer_sale_order_line_id','=',line.name.dealer_sale_order_id.id),('retur_lot_id','=',line.name.id),('retur_id.state','not in',['draft','cancel'])], limit=1)
                    obj = mod_obj.browse(cr, uid, obj_ids)
                    titipan = obj.price_bbn or 0.0
                    if not titipan:
                        return res
            margin = titipan - (line.total_tagihan or 0.0) + (line.pajak_progressive or 0.0) + (line.total_jasa or 0.0)
            res[line.id]['koreksi'] = koreksi
            res[line.id]['titipan'] = titipan
            res[line.id]['margin'] = margin
        return res

    _columns = {
        'koreksi': fields.function(_amount_line, digits_compute=dp.get_precision('Account'), string='Koreksi', multi='sums', help="Koreksi.", track_visibility='always'),
        'margin': fields.function(_amount_line, digits_compute=dp.get_precision('Account'), string='Margin', multi='sums', help="Margin."),
        'titipan': fields.function(_amount_line, digits_compute=dp.get_precision('Account'), string='Titipan', multi='sums', help="Titipan."),
        'is_opbal': fields.related(
            'proses_biro_jasa_id', 'is_opbal', type='boolean',
            relation='dym.proses.birojasa', string='OBL', readonly=False),
    }

    def onchange_total_tagihan(self, cr, uid, ids, name, total_tagihan, total_estimasi, pajak_progressive, is_opbal, context=None):
        tbj_line = self.browse(cr, uid, ids, context=context)
        if not all([name,total_tagihan]):
            return False
        value = {
            'koreksi': 0.0,
            'titipan': 0.0,
            'margin': 0.0,
        }
        engine_id = self.pool.get('stock.production.lot').browse(cr, uid, name, context=context)
        koreksi = (total_tagihan or 0.0) -  (total_estimasi or 0.0) -  (pajak_progressive or 0.0)
        if is_opbal:
            opbal_obj = self.pool.get('opbal.customer.deposit')
            titipan_stnk_id = opbal_obj.search(cr, uid, [('engine_id','=',engine_id.id)], context=context)
            if not titipan_stnk_id:
                return {
                    'warning': {
                            'title': _('Error!'), 
                            'message': _('Nomor mesin %s tidak ditemukan di tabel opbal titipan stnk. Mohon isi di Advance Setting > Opbal Setting > Titipan STNK' % engine_id.name)
                        }, 
                    'value': {
                        'total_tagihan': 0.0
                    }
                }
            titipan_stnk = opbal_obj.browse(cr, uid, titipan_stnk_id, context=context)
            titipan = titipan_stnk.amount or 0.0
            if not titipan:
                return {
                    'warning': {
                            'title': _('Error!'), 
                            'message': _('Titipan STNK untuk nomor mesin %s sebesar nol. Mohon isi di Advance Setting > Opbal Setting > Titipan STNK' % engine_id.name)
                        }, 
                    'value': {
                        'total_tagihan': 0.0
                    }
                }
        else:
            titipan = 0.0
            model = 'dealer.sale.order.line'
            obj_ids = self.pool.get(model).search(cr, uid, [('dealer_sale_order_line_id','=',engine_id.dealer_sale_order_id.id),('lot_id','=',engine_id.id)], limit=1)
            if not obj_ids:
                model = 'dym.retur.jual.line'
                obj_ids = self.pool.get(model).search(cr, uid, [('dso_line_id.dealer_sale_order_line_id','=',engine_id.dealer_sale_order_id.id),('retur_lot_id','=',engine_id.id),('retur_id.state','not in',['draft','cancel'])], limit=1)
            obj = self.pool.get(model).browse(cr, uid, obj_ids)
            titipan = obj.price_bbn or 0.0
            if not titipan:
                return {
                    'warning': {
                            'title': _('Error!'), 
                            'message': _('Titipan STNK untuk nomor mesin %s sebesar nol. Mungkin ini data dari Opbal, coba centang field OBL.' % engine_id.name)
                        }, 
                    'value': {
                        'total_tagihan': 0.0
                    }
                }
        margin = titipan - (total_tagihan or 0.0) + (pajak_progressive or 0.0) + (tbj_line.total_jasa or 0.0)
        value['koreksi'] = koreksi
        value['titipan'] = titipan
        value['margin'] = margin
        return {
            'value': value,
        }
