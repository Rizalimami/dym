import time

import openerp
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import api, models
from datetime import datetime, date
import fungsi_terbilang


class dym_kwitansi_pelunasan_leasing_multi(osv.osv_memory):
    _name = 'dym.kwitansi.pelunasan.leasing.multi'
    _description = 'Kwitansi Pelunasan Leasing'
    _columns = {
        'partner_id' : fields.many2one('res.partner', 'Finco', domain=[('finance_company','=',True)], required=True),
        'finco_cabang': fields.many2one('dym.cabang.partner','Cabang Finco'),
        'branch_id' : fields.many2one('dym.branch', 'Cabang', required=True),
        'untuk_pembayaran': fields.char('Untuk Pembayaran', required=True),
        'dso_ids': fields.many2many('dealer.sale.order', 'dym_kwitansi_pelunasan_leasing_dso_rel', 'dym_kwitans_pelunasan_leasing_wizard_id','dso_id', 'Dealer Sales Memo', copy=False),
    }        

    _defaults = {
    }

    def fill_dso(self, cr, uid, ids, partner_id,finco_cabang,branch_id, context=None):
        domain = [
            ('state','in',['progress','done']),
            ('branch_id','=',branch_id),
            ('finco_id','=',partner_id),
            ('finco_cabang','=?',finco_cabang)
        ]
        dso_ids = self.pool.get('dealer.sale.order').search(cr, uid, domain)
        dso = self.pool.get('dealer.sale.order').browse(cr, uid, dso_ids)
        filter_ids = []
        for val in dso:
            obj_inv = self.pool.get('account.invoice')
            if val.finco_id and val.is_credit == True:
                inv_id = obj_inv.search(cr,uid,[
                                             ('origin','ilike',val.name),
                                             ('partner_id','in',[val.partner_id.id,val.finco_id.id]),
                                             ('tipe','=','finco')
                                             ])
                inv_status = obj_inv.browse(cr,uid,inv_id)
            else:
                inv_id = obj_inv.search(cr,uid,[
                                             ('origin','ilike',val.name),
                                             ('partner_id','=',val.partner_id.id),
                                             ('tipe','=','customer')
                                             ])
                inv_status = obj_inv.browse(cr,uid,inv_id)
            if not(inv_status.state == 'paid' or inv_status.residual == 0):
                filter_ids.append(val.id)
        domain_dso = {'dso_ids':[('id','in',filter_ids)]}
        return {'domain':domain_dso}

    def onchange_dso(self, cr, uid, ids, dso_list, context=None):
        total_line = len(dso_list[0][2])
        terbilang_line = self.pool.get('dealer.sale.order').get_terbilang(cr, uid, ids, total_line, print_subsidi_tax=True).upper()
        res = {}
        res['value'] = {}
        res['value']['untuk_pembayaran'] = ('%s (%s) UNIT SEPEDA MOTOR HONDA + BIAYA PENGURUSAN STNK DAN BPKB') % (str(total_line), str(terbilang_line))
        return res

class kwitansi_gc(models.AbstractModel):
    _name = 'report.dym_kwitansi_pelunasan_leasing.report_kwitansi_pelunasan_leasing_multi_template'

    def render_html(self, cr, uid, ids, data=None, context=None):
        registry = openerp.registry(cr.dbname)
        check_wizard = registry.get('dym.kwitansi.pelunasan.leasing.multi').read(cr, uid, ids, context=context)

        if check_wizard:

            data_wizard = check_wizard[0]
            partner_id = data_wizard['partner_id'][0]
            branch_id = data_wizard['branch_id'][0]
            if data_wizard['finco_cabang']:
                finco_cabang = data_wizard['finco_cabang'][0]
            else:
                finco_cabang = []

            obj_partner = registry.get('res.partner')
            obj_finco_cabang = registry.get('dym.cabang.partner')
            obj_dso = registry.get('dealer.sale.order')
            obj_branch = registry.get('dym.branch')

            total = 0
            dso_ids = data_wizard['dso_ids']
            dsos = obj_dso.browse(cr, uid, dso_ids)

            for dso_id in dso_ids:
                obj_dso._set_bill_date(cr, uid, dso_id)

            tanggal = date.today().strftime('%Y-%m-%d')
            partner = obj_partner.browse(cr, uid, partner_id)
            finco_cabang = obj_finco_cabang.browse(cr, uid, finco_cabang)
            branch = obj_branch.browse(cr, uid, branch_id)

            total = 0
            for dso in dsos:
                for line in dso.dealer_sale_order_line:
                    total += line.price_unit+line.price_bbn-line.uang_muka
            untuk_pembayaran = data_wizard['untuk_pembayaran']
            terbilang = fungsi_terbilang.terbilang(total, "idr", 'id', print_subsidi_tax=False)
                
        report_obj = self.pool['report']
        report = report_obj._get_report_from_name(cr, uid, 'dym_kwitansi_pelunasan_leasing.report_kwitansi_pelunasan_leasing_multi_template')
        docargs = {'doc_ids': ids,'doc_model': report.model,'docs': data, 'untuk_pembayaran': untuk_pembayaran, 'total':total, 'terbilang': terbilang, 'partner': partner, 'finco_cabang': finco_cabang, 'tanggal':tanggal, 'branch':branch, 'dsos':dsos}
        return report_obj.render(cr, uid, ids, 'dym_kwitansi_pelunasan_leasing.report_kwitansi_pelunasan_leasing_multi_template', docargs, context=context)