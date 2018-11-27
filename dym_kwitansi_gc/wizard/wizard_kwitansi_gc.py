import time

import openerp
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import api, models
from datetime import datetime, date
import fungsi_terbilang


class dym_kwitansi_gc(osv.osv_memory):
    _name = 'dym.kwitansi.gc'
    _description = 'Kwitansi GC'
    _columns = {
        'partner_id' : fields.many2one('res.partner', 'Customer', required=True),
        'branch_id' : fields.many2one('dym.branch', 'Cabang', required=True),
        'untuk_pembayaran': fields.char('Untuk Pembayaran', required=True),
        'invoice_ids': fields.many2many('account.invoice', 'dym_kwitansi_gc_invoice_rel', 'dym_kwitans_gc_wizard_id','invoce_id', 'Invoices', copy=False),
    }        

    _defaults = {
    }


class kwitansi_gc(models.AbstractModel):
    _name = 'report.dym_kwitansi_gc.report_kwitansi_gc_template'

    def render_html(self, cr, uid, ids, data=None, context=None):
        registry = openerp.registry(cr.dbname)
        check_wizard = registry.get('dym.kwitansi.gc').read(cr, uid, ids, context=context)

        if check_wizard:

            data_wizard = check_wizard[0]
            partner_id = data_wizard['partner_id'][0]
            branch_id = data_wizard['branch_id'][0]

            obj_partner = registry.get('res.partner')
            obj_inv = registry.get('account.invoice')
            obj_branch = registry.get('dym.branch')

            total = 0
            invoice_ids = data_wizard['invoice_ids']
            invoice = obj_inv.browse(cr, uid, invoice_ids)

            tanggal = date.today().strftime('%Y-%m-%d')
            partner = obj_partner.browse(cr, uid, partner_id)
            branch = obj_branch.browse(cr, uid, branch_id)

            total = sum(inv.residual for inv in invoice)
            untuk_pembayaran = data_wizard['untuk_pembayaran']
            terbilang = fungsi_terbilang.terbilang(total, "idr", 'id', print_subsidi_tax=False)
                
        report_obj = self.pool['report']
        report = report_obj._get_report_from_name(cr, uid, 'dym_kwitansi_gc.report_kwitansi_gc_template')
        docargs = {'doc_ids': ids,'doc_model': report.model,'docs': data, 'untuk_pembayaran': untuk_pembayaran, 'total':total, 'terbilang': terbilang, 'partner': partner, 'tanggal':tanggal, 'branch':branch, 'invoice':invoice}
        return report_obj.render(cr, uid, ids, 'dym_kwitansi_gc.report_kwitansi_gc_template', docargs, context=context)