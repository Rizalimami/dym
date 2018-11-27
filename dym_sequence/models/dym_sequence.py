import time
from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp import tools, api, _
from select import select
from openerp import api, _

import logging
_logger = logging.getLogger(__name__)

class dym_ir_sequence(osv.osv):
    _inherit = 'ir.sequence'

    def get_kode_divisi(self, cr, uid, division, context=None):
        if division == 'Unit':
            return '-S'
        elif division == 'Sparepart':
            return '-W'
        elif division == 'Finance':
            return '-F'
        elif division == False:
            return ''
        else:
            return '-G'

    def get_nik_per_branch(self, cr, uid, branch_id, context=None):
        doc_code = self.pool.get('dym.branch').browse(cr, uid, branch_id).doc_code
        seq_name = '{0}{1}'.format('EMP', doc_code)

        ids = self.search(cr, uid, [('name','=',seq_name)])
        if not ids:
            user = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context=context)
            prefix = '%(y)s%(month)s'
            prefix = doc_code + prefix
            ids = self.create(cr, SUPERUSER_ID, {'name':seq_name,
                'implementation':'no_gap',
                'prefix':prefix,
                'company_id':user.company_id.id,
                'padding':3
            })

        return self.get_id(cr, uid, ids)


    def get_per_branch(self, cr, uid, branch_id, prefix, division=False, context=None):
        if not branch_id:
            return False
        branch = self.pool.get('dym.branch').browse(cr, uid, branch_id)
        doc_code = branch.doc_code
        company_id = branch.company_id
        if not company_id:
            raise osv.except_osv(_('Error!'),_("Branch '%s' tidak memiliki company, mohon disetting dulu (Branch ID:%s)." % (branch.name,branch.id) ))
        kode_divisi = self.get_kode_divisi(cr, uid, division, context=context)
        if not doc_code:
            raise osv.except_osv(_('Error!'),_("System akan mencari / membuat penomoran dokumen per cabang, tapi kode dokumen cabang tidak ditemukan. Untuk itu, silahkan lengkapi dulu di Advance Setting > Branch: 'Document Code'."))
        if not prefix:
            raise osv.except_osv(_('Error!'),_("System akan mencari / membuat penomoran dokumen per cabang, tapi prefix dokumen tidak ditemukan. Untuk itu, silahkan lengkapi dulu di Accounting > Configuration > Journal: Code."))
        prefix_divisi = '%s%s' % (prefix,kode_divisi)
        seq_name = '{0}/{1}'.format(prefix_divisi, doc_code)
        user = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context=context)
        prefix = '%s%s' % (seq_name,'/%(y)s%(month)s/')
        ids = self.search(cr, uid, [('name','=',seq_name),('company_id','=',company_id.id)])
        if not ids:
            values = {
                'name':seq_name,
                'implementation':'no_gap',
                'prefix':prefix,
                'company_id':company_id.id,
                'padding':5
            }
            ids = self.create(cr, SUPERUSER_ID, values, context=context)
        else:
            ids = ids[0]
        res = self.next_by_id(cr, SUPERUSER_ID, ids, context=context)
        return res

    def get_sequence(self, cr, uid, first_prefix, division=False, padding=5, branch=None, context=None):
        kode_divisi = self.get_kode_divisi(cr, uid, division, context=context)
        first_prefix = first_prefix+kode_divisi
        if branch:
            first_prefix = '%s/%s' % (first_prefix,branch.code)
        ids = self.search(cr, uid, [('name','=',first_prefix),('padding','=',padding)])
        if not ids:
            prefix = first_prefix + '/%(y)s%(month)s/'
            ids = self.create(cr, SUPERUSER_ID, {'name': first_prefix,
                                 'implementation': 'no_gap',
                                 'prefix': prefix,
                                 'padding': padding})
            
        return self.get_id(cr, SUPERUSER_ID, ids)
    
    def get_sequence_asset_category(self, cr, uid, first_prefix, context=None):
        ids = self.search(cr, uid, [('name','=',first_prefix)])
        if not ids:
            prefix = first_prefix + '/%(y)s%(month)s/'
            ids = self.create(cr, SUPERUSER_ID, {
                            'name': first_prefix,
                            'implementation': 'no_gap',
                            'prefix': prefix,
                            'padding': 4})        
        return self.get_id(cr, SUPERUSER_ID, ids)
