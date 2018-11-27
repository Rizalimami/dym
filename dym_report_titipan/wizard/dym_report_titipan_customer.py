import time
from openerp.osv import orm, fields,osv
import logging
_logger = logging.getLogger(__name__)
from lxml import etree
from datetime import datetime

class report_titipan_customer(orm.TransientModel):
    _name = 'dym.report.titipan_customer'
    _rec_name = 'titipan'
    _description = 'Laporan Titipan'
 
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(report_titipan_customer, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]
        
        doc = etree.XML(res['arch'])      
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        nodes_journal_ids = doc.xpath("//field[@name='journal_ids']")
        nodes_journal = doc.xpath("//field[@name='journal_id']")
        for node in nodes_branch:
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        for node in nodes_journal:
            node.set('domain', '[("branch_id", "in", '+ str(branch_ids+[False])+'),("type","=","pettytitipan_customer")]')  
        for node in nodes_journal_ids:
            node.set('domain', '[("branch_id", "in", '+ str(branch_ids+[False])+')]')                        
        res['arch'] = etree.tostring(doc)
        return res
    
    _columns = {
        'titipan': fields.selection([
            ('2105000 Titipan','2105000 Titipan'),
            ('2105001 Titipan Uang Muka Konsumen','2105001 Titipan Uang Muka Konsumen'),
            ('2105002 Titipan STNK','2105002 Titipan STNK'),
            ('2105003 Titipan Asuransi','2105003 Titipan Asuransi'),
            ('2105004 Titipan Mekanik','2105004 Titipan Mekanik'),
            ('2105005 Titipan Belum Di Apply','2105005 Titipan Belum Di Apply'),
            ('2105006 Titipan Karyawan','2105006 Titipan Karyawan'),
            ('2105007 Titipan Asuransi Kecelakaan','2105007 Titipan Asuransi Kecelakaan'),
            ('2105008 Titipan Dana Pensiun','2105008 Titipan Dana Pensiun'),
            ('2105009 Titipan Kesehatan BPJS','2105009 Titipan Kesehatan BPJS'),
            ('2105010 Titipan JHT BPJS','2105010 Titipan JHT BPJS'),
            ('2105011 Titipan Tidak Teridentifikasi','2105011 Titipan Tidak Teridentifikasi'),
            ('2105012 Titipan PPh','2105012 Titipan PPh'),
            ('2105013 Titipan Leasing','2105013 Titipan Leasing'),
            ('2105014 Titipan Pelanggaran Wilayah','2105014 Titipan Pelanggaran Wilayah'),
            ('2105015 Titipan Main Dealer','2105015 Titipan Main Dealer'),
            ('2105016 Titipan Discount Program','2105016 Titipan Discount Program'),
            ('2105017 Titipan Advance Payment FIF','2105017 Titipan Advance Payment FIF'),
            ('2105099 Titipan Lain-lain','2105099 Titipan Lain-lain')
            ], 'titipan', change_default=True, select=True), 
        'status': fields.selection([
            ('outstanding','Outstanding'),
            ('reconcile','Reconciled')
            ], 'Status', change_default=True, select=True),         
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'branch_ids': fields.many2many('dym.branch', 'dym_report_titipan_customer_branch_rel', 'dym_report_titipan_customer',
            'branch_id', 'Branch', copy=False),
        'journal_ids': fields.many2many('account.journal', 'dym_report_titipan_customer_journal_rel', 'dym_report_titipan_customer',
            'journal_id', 'Journal', copy=False, ),             
        'journal_id' : fields.many2one('account.journal',string="Journal",domain="[('type','=','pettytitipan_customer')]")                                 
    }

    _defaults = {
        #'start_date':fields.date.context_today,
        #'end_date':fields.date.context_today,
        #'titipan':'2105001 Titipan Uang Muka Konsumen'
    }    
    
    def print_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        data = self.read(cr, uid, ids)[0]
        branch_ids = data['branch_ids']
        cek=len(branch_ids)
        if cek == 0:
            branch_ids=[b.id for b in branch_ids_user]
        else:
            branch_ids=data['branch_ids']
        titipan = data['titipan']
        journal_ids = data['journal_ids']
        journal_id = data['journal_id']
        status = data['status']
        start_date = data['start_date']
        end_date = data['end_date']
        data.update({
            'branch_ids': branch_ids,
            'start_date': start_date,
            'end_date': end_date,
        })
        print "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", titipan
        if context.get('titipan') in (
                '2105000 Titipan',
                '2105001 Titipan Uang Muka Konsumen',
                '2105002 Titipan STNK',
                '2105003 Titipan Asuransi',
                '2105004 Titipan Mekanik',
                '2105005 Titipan Belum Di Apply',
                '2105006 Titipan Karyawan',
                '2105007 Titipan Asuransi Kecelakaan',
                '2105008 Titipan Dana Pensiun',
                '2105009 Titipan Kesehatan BPJS',
                '2105010 Titipan JHT BPJS',
                '2105011 Titipan Tidak Teridentifikasi',
                '2105012 Titipan PPh',
                '2105013 Titipan Leasing',
                '2105014 Titipan Pelanggaran Wilayah',
                '2105015 Titipan Main Dealer',
                '2105016 Titipan Discount Program',
                '2105017 Titipan Advance Payment FIF',
                '2105099 Titipan Lain-lain'
                ):
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'Laporan Titipan',
                'datas': data
            }        
        else:
            context['landscape'] = True
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'Laporan Titipan',
                'datas': data
            } 

    def xls_export(self, cr, uid, ids, context=None):
        res = self.print_report(cr, uid, ids, context)
        return res
