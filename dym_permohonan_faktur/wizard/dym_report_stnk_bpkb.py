import time
from openerp.osv import orm, fields,osv
import logging
_logger = logging.getLogger(__name__)
from lxml import etree

class report_stnk_bpkb(orm.TransientModel):
    _name = 'report.stnk.bpkb'
    _description = 'Report STNK BPKB'
 
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context: context = {}
        res = super(report_stnk_bpkb, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        categ_ids = self.pool.get('product.category').get_child_ids(cr,uid,view_id,'Unit')
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        branch_ids=[b.id for b in branch_ids_user]
        
        doc = etree.XML(res['arch'])
        nodes_stnk_loc = doc.xpath("//field[@name='loc_stnk_ids']")
        nodes_bpkb_loc = doc.xpath("//field[@name='loc_bpkb_ids']")       
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        for node in nodes_stnk_loc:
            node.set('domain', '[("branch_id", "=", '+ str(branch_ids)+')]')
        for node in nodes_branch:
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        for node in nodes_bpkb_loc:
            node.set('domain', '[("branch_id", "=", '+ str(branch_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res
    
    _columns = {
 
        'branch_ids': fields.many2many('dym.branch', 'report_stnk_bpkb_rel', 'report_stnk_bpkb_wizard_id',
                                        'branch_id', 'Branch', copy=False),
        'lot_ids': fields.many2many('stock.production.lot', 'report_lot_rel', 'report_stnk_bpkb_wizard_id',
                                        'lot_id', 'Engine No', copy=False, ),
        'loc_stnk_ids': fields.many2many('dym.lokasi.stnk', 'report_lokasi_stnk_rel', 'report_stnk_bpkb_wizard_id',
                                        'stnk_id', 'Lokasi STNK', copy=False),
        'loc_bpkb_ids': fields.many2many('dym.lokasi.bpkb', 'report_lokasi_bpkb_rel', 'report_stnk_bpkb_wizard_id',
                                        'bpkb_id', 'Lokasi BPKB', copy=False),\
        'partner_ids': fields.many2many('res.partner', 'report_partner_rel', 'report_stnk_bpkb_wizard_id',
                                        'partner_id', 'Customer', copy=False,domain="[('customer','!=',False)]"),
        'birojasa_ids': fields.many2many('res.partner', 'report_birojasa_rel', 'report_stnk_bpkb_wizard_id',
                                        'partner_id', 'Biro Jasa', copy=False,domain="[('biro_jasa','!=',False)]"),
        'finco_ids': fields.many2many('res.partner', 'report_finco_rel', 'report_stnk_bpkb_wizard_id',
                                        'partner_id', 'Finco', copy=False,domain="[('finance_company','!=',False)]"),                                
    }
    
    def create(self,cr,uid,vals,context=None):
        search = []
        if vals['lot_ids'] :
            for x in vals['lot_ids'] :                
                if x[2] :
                    search.append(('id','in',x[2]))
        if vals['branch_ids'] :
            for x in vals['branch_ids'] :                
                if x[2] :
                    search.append(('branch_id','in',x[2]))    
        if vals['loc_stnk_ids'] :
            for x in vals['loc_stnk_ids'] :                
                if x[2] :
                    search.append(('lokasi_stnk_id','in',x[2])) 
        if vals['loc_bpkb_ids'] :
            for x in vals['loc_bpkb_ids'] :                
                if x[2] :
                    search.append(('lokasi_bpkb_id','in',x[2])) 
        if vals['partner_ids'] :
            for x in vals['partner_ids'] :                
                if x[2] :
                    search.append(('customer_id','in',x[2])) 
        if vals['birojasa_ids'] :
            for x in vals['birojasa_ids'] :                
                if x[2] :
                    search.append(('biro_jasa_id','in',x[2])) 
        if vals['finco_ids'] :
            for x in vals['finco_ids'] :                
                if x[2] :
                    search.append(('finco_id','in',x[2]))                                                                                             

        search_lot = self.pool.get('stock.production.lot').search(cr,uid,search)
        if not search_lot :
            raise osv.except_osv(('No Data Available !'), ("No records found for your selection!"))            
        
        res = super(report_stnk_bpkb,self).create(cr,uid,vals,context=context)
        return res
    
    def print_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        branch_ids_user=self.pool.get('res.users').browse(cr,uid,uid).branch_ids
        data = self.read(cr, uid, ids)[0]
        branch_ids = data['branch_ids']
        cek=len(branch_ids)
        
        if cek == 0 :
            branch_ids=[b.id for b in branch_ids_user]
        else :
            branch_ids=data['branch_ids']
        
        partner_ids = data['partner_ids']
        loc_stnk_ids = data['loc_stnk_ids']
        loc_bpkb_ids = data['loc_bpkb_ids']
        lot_ids = data['lot_ids']
        birojasa_ids = data['birojasa_ids']
        finco_ids = data['finco_ids']

        data.update({
            'branch_ids': branch_ids,
            'partner_ids': partner_ids,
            'loc_stnk_ids': loc_stnk_ids,
            'loc_bpkb_ids': loc_bpkb_ids,
            'lot_ids': lot_ids,
            'birojasa_ids': birojasa_ids,
            'finco_ids': finco_ids,
            
        })
        if context.get('xls_export'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'dym_report_stnk_bpkb_xls',
                    'datas': data}
        else:
            context['landscape'] = True
            return self.pool['report'].get_action(
                cr, uid, [],
                'dym_permohonan_faktur.report_stnk_bpkb',
                data=data, context=context)

    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)
