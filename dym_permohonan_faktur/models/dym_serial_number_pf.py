import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import Warning as UserError, RedirectWarning
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
  
class dym_stock_production_lot_wizard_permohonan_faktur(osv.osv):
    _inherit = 'stock.production.lot'
    _columns = {
        'permohonan_faktur_id': fields.many2one('dym.permohonan.faktur',string="No Permohonan Faktur"), 
        'penerimaan_faktur_id': fields.many2one('dym.penerimaan.faktur',string="No Penerimaan Faktur"), 
        'tgl_cetak_faktur' : fields.date('Tgl Cetak Faktur'),
        'cddb_id' : fields.many2one('dym.cddb',domain="[('customer_id','=',customer_id)]",string="CDDB"),
        'lot_status_cddb' : fields.selection([('not','Not Ok'),('ok','OK'),('udstk','UDSTK OK'),('cddb','CDDB OK')],string="CDDB State"),
        'invoice_bbn' : fields.many2one('account.invoice','Invoice BBN',domain=[('type','=','in_invoice')]),
        'tgl_bayar_birojasa' : fields.date('Tgl Bayar Biro Jasa'),
        'tgl_penyerahan_faktur' : fields.date('Tgl Penyerahan Faktur'),
        'penyerahan_faktur_id' : fields.many2one('dym.penyerahan.faktur',string="No Penyerahan Faktur"), 
        'plat' : fields.selection([('H','H'),('M','M')], 'Plat'),
    }
    
    _defaults = {
        'lot_status_cddb':'not'
    }

    def get_customer_database(self,cr,uid,ids,context=None):
        vals = self.browse(cr,uid,ids)
        form_id  = 'dym.cddb.wizard.form.view'
        view_pool = self.pool.get("ir.ui.view")
        vit = view_pool.search(cr,uid, [
                                     ("name", "=", form_id), 
                                     ("model", "=", 'dym.cddb'), 
                                    ])
        form_browse = view_pool.browse(cr,uid,vit)
        return {
            'name': 'Form CDDB',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'dym.cddb',
            'type': 'ir.actions.act_window',
            'view_id' : form_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': vals.cddb_id.id
            } 
    
    def get_atasnama_stnk(self,cr,uid,ids,context=None):
        warn = {}
        vals = self.browse(cr,uid,ids)
        form_id  = 'dym.atas.nama.stnk.wizard.form'
        view_pool = self.pool.get("ir.ui.view")
        vit = view_pool.search(cr,uid, [
                                     ("name", "=", form_id), 
                                     ("model", "=", 'res.partner'), 
                                    ])
        form_browse = view_pool.browse(cr,uid,vit)
        udstk = vals.customer_stnk.id
        if udstk :
            return {
                'name': 'Atas Nama STNK',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'res.partner',
                'type': 'ir.actions.act_window',
                'view_id' : form_browse.id,
                'nodestroy': True,
                'target': 'new',
                'res_id': udstk
                } 
        else :
            return False

    def get_edit_udstk(self,cr,uid,ids,context=None):
        vals = self.browse(cr,uid,ids)
        form_id  = 'edit.udstk.wizard.form'
        view_pool = self.pool.get("ir.ui.view")
        vit = view_pool.search(cr,uid, [
                                     ("name", "=", form_id), 
                                     ("model", "=", 'stock.production.lot'), 
                                    ])
        form_browse = view_pool.browse(cr,uid,vit)
        return {
            'name': 'UDSTNK',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.production.lot',
            'type': 'ir.actions.act_window',
            'view_id' : form_browse.id,
            'nodestroy': True,
            'target': 'new',
            'res_id': vals.id
            } 

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('customer_stnk',False):
            cddb_id = self.pool.get('dym.cddb').search(cr, uid, [('customer_id','=',vals['customer_stnk'])], context=context)
            if cddb_id:
                vals['cddb_id'] = cddb_id[0]
            else:
                raise UserError(_('Maaf, CDDB tidak ditemukan ..!'))
        return super(dym_stock_production_lot_wizard_permohonan_faktur, self).write(cr, uid, ids, vals, context=context)

    def _report_xls_stnk_bpkb_fields(self, cr, uid, context=None):
        return [
            'branch_id',\
            'engine_no',\
            'chassis_no',\
            'nama_customer',\
            'mobile_customer',\
            'lokasi_stnk',\
            'lokasi_bpkb',\
            'location_name',\
            'supplier_name',\
            'stnk_name',\
            'state',\
            'finco_name',\
            'birojasa_name',\
            'sale_order',\
            'tgl_sale_order',\
            'purchase_order',\
            'tgl_purchase_order',\
            'no_permohonan_faktur',\
            'tgl_faktur',\
            'no_penerimaan_faktur',\
            'tgl_terima',\
            'no_faktur',\
            'tgl_cetak_faktur',\
            'no_penyerahan_faktur',\
            'tgl_penyerahan_faktur',\
            'no_proses_stnk',\
            'tgl_proses_stnk',\
            'no_proses_birojasa',\
            'tgl_proses_birojasa',\
            'no_penerimaan_stnk',\
            'no_penerimaan_notice',\
            'no_penerimaan_no_polisi',\
            'no_penerimaan_bpkb',\
            'no_notice',\
            'no_bpkb',\
            'no_polisi',\
            'no_stnk',\
            'tgl_notice',\
            'tgl_stnk',\
            'tgl_bpkb',\
            'no_urut_bpkb',\
            'tgl_terima_stnk',\
            'tgl_terima_bpkb',\
            'tgl_terima_notice',\
            'tgl_terima_no_polisi',\
            'no_penyerahan_stnk',\
            'no_penyerahan_notice',\
            'no_penyerahan_polisi',\
            'no_penyerahan_bpkb',\
            'tgl_penyerahan_stnk',\
            'tgl_penyerahan_notice',\
            'tgl_penyerahan_plat',\
            'tgl_penyerahan_bpkb',\
            'no_pengurusan_stnk_bpkb',\
            'tgl_pengurusan_stnk_bpkb',\
            'aging_stnk',\
            'aging_bpkb',                                  
        ]

    def _report_xls_arap_details_fields(self, cr, uid, context=None):
        return [
            'document', 'date', 'date_maturity', 'account', 'description',
            'rec_or_rec_part', 'debit', 'credit', 'balance',
        ]

    def _report_xls_arap_overview_template(self, cr, uid, context=None):
        return {}

    def _report_xls_arap_details_template(self, cr, uid, context=None):
        return {}
