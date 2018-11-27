import time

import openerp
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import api, models
from datetime import datetime, date, timedelta
from lxml import etree

class dym_stock_move(osv.osv):
    _inherit = 'stock.move'


    def get_ito(self, cr, uid, ids, first_date, date, move, context=None):
        if move.location_dest_id.usage in ['internal','nrfs','kpb'] and move.location_dest_id.branch_id.id == move.branch_id.id:
            stock_qty = move.total_stock_destination
        elif move.location_id.usage in ['internal','nrfs','kpb'] and move.location_id.branch_id.id == move.branch_id.id:
            stock_qty = move.total_stock_source
        if stock_qty <= 0:
            return '-'

        sales_qty = 0
        if move.product_id.categ_id.isParentName('Unit'):
            dsol_src = self.pool.get('dealer.sale.order.line').search(cr, uid, [('dealer_sale_order_line_id.state','=','done'),('product_id','=',move.product_id.id),('dealer_sale_order_line_id.date_order','<=',date),('dealer_sale_order_line_id.date_order','>=',first_date)])
            dsol_brw = self.pool.get('dealer.sale.order.line').browse(cr, uid, dsol_src)
            for dsol_obj in dsol_brw:
                sales_qty += dsol_obj.product_qty

        if move.product_id.categ_id.isParentName('Sparepart'):
            wol_src = self.pool.get('dym.work.order.line').search(cr, uid, [('work_order_id.state','=','done'),('product_id','=',move.product_id.id),('work_order_id.date','<=',date),('work_order_id.date','>=',first_date)])
            wol_brw = self.pool.get('dym.work.order.line').browse(cr, uid, wol_src)
            for wol_obj in wol_brw:
                sales_qty += wol_obj.product_qty

            sol_src = self.pool.get('sale.order.line').search(cr, uid, [('order_id.state','=','done'),('product_id','=',move.product_id.id),('order_id.division','=','Sparepart'),('order_id.date_order','<=',date),('order_id.date_order','>=',first_date)])
            sol_brw = self.pool.get('sale.order.line').browse(cr, uid, sol_src)
            for sol_obj in sol_brw:
                sales_qty += sol_obj.product_uom_qty

        if sales_qty == 0:
            return '-'

        ito = float(stock_qty/sales_qty)
        return ito

    def get_stock_days(self, cr, uid, ids, ito, first_date, date, context=None):
        if ito == '-':
            return '-'
        # date_diff = int((datetime.date(datetime.strptime(date, '%Y-%m-%d'))-datetime.date(datetime.strptime(first_date, '%Y-%m-%d'))).days)
        val = self.browse(cr, uid, ids)[0]
        date_diff = self.pool.get('dym.work.days').get_date_diff(cr, uid, ids, first_date, date, val.picking_id.branch_id.id)
        stock_days = float(ito*date_diff)
        return str(stock_days) + ' hari'

    _columns = {
                'total_stock_source': fields.float(string='Total Stock Source Location'),
                'total_stock_destination': fields.float(string='Total Stock Destiation Location'),
                'total_stock_source_branch': fields.float(string='Total Stock Source Branch'),
                'total_stock_destination_branch': fields.float(string='Total Stock Destiation Branch'),
            }

    def save_available(self, cr, uid, ids, id_product, id_location, id_branch=False, context=None):
        if id_branch:
            if context == None:
                context = {}
            product = self.pool.get('product.product').browse(cr, uid, id_product, context=context)
            rfs = product.with_context(branch_id=id_branch).stock_rfs
            nrfs = product.with_context(branch_id=id_branch).stock_nrfs
            rfs = rfs if rfs != '-' else 0
            nrfs = nrfs if nrfs != '-' else 0
            qty = rfs + nrfs
        else:        
            quants = self.pool.get('stock.quant').search(cr, uid, [('product_id','=',id_product),('location_id','=',id_location)])
            quants_brw = self.pool.get('stock.quant').browse(cr, uid, quants)
            qty = 0
            for quant in quants_brw:
                qty += quant.qty
        return qty

    def action_done(self, cr, uid, ids, context=None):
        vals = super(dym_stock_move,self).action_done(cr,uid,ids,context=context)
        for move in self.browse(cr, uid, ids):
            total_stock_source = 0
            total_stock_destination = 0
            total_stock_source_branch = 0
            total_stock_destination_branch = 0
            if move.location_id.usage in ['internal','nrfs','kpb']:
                total_stock_source = self.save_available(cr, uid, [move.id], move.product_id.id, move.location_id.id, context=context)
                total_stock_source_branch = self.save_available(cr, uid, [move.id], move.product_id.id, move.location_id.id, id_branch=move.picking_id.branch_id.id or move.inventory_id.branch_id.id or move.branch_id.id, context=context)
            if move.location_dest_id.usage in ['internal','nrfs','kpb']:
                total_stock_destination = self.save_available(cr, uid, [move.id], move.product_id.id, move.location_dest_id.id, context=context)
                total_stock_destination_branch = self.save_available(cr, uid, [move.id], move.product_id.id, move.location_dest_id.id, id_branch=move.picking_id.branch_id.id or move.inventory_id.branch_id.id or move.branch_id.id, context=context)
            self.write(cr,uid,[move.id],{'total_stock_source':total_stock_source,'total_stock_destination':total_stock_destination})    
        return vals

class dym_ito_report(osv.osv_memory):

    _name = 'dym.ito.report'
    _description = 'Laporan ITO'

    def _get_branch_ids(self, cr, uid, context=None):
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context:
            context = {}
        res = super(dym_ito_report, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        branch_ids = self._get_branch_ids(cr, uid, context)
        doc = etree.XML(res['arch'])
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        for node in nodes_branch :
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res

    _columns = {
        'branch_ids': fields.many2many('dym.branch', 'dym_report_ito_branch_rel', 'dym_report_ito_wizard_id',
            'branch_id', 'Branches', copy=False),
        'division':fields.selection([('Unit','Showroom'),('Sparepart','Workshop')], 'Division'),
        'product_ids': fields.many2many('product.product', 'dym_report_ito_product_rel', 'dym_report_ito_wizard_id','product_id', 'Products'),
        'date': fields.date('Date', required=True),
    }        

    def _get_categ_ids(self, cr, uid, categ_name, context=None):
        obj_categ = self.pool.get('product.category')
        all_categ_ids = obj_categ.search(cr, uid, [])
        categ_ids = obj_categ.get_child_ids(cr, uid, all_categ_ids, categ_name)
        return categ_ids

    def onchange_division(self, cr, uid, ids, division, context=None):
        value = {}
        domain = {}
        warning = {}
        value['product_ids'] = False
        if division:
            categ_ids = self._get_categ_ids(cr, uid, division, context)
            domain['product_ids'] = [('categ_id','in',categ_ids)]
        else:
            categ_ids = self._get_categ_ids(cr, uid, 'Unit', context)
            categ_ids += self._get_categ_ids(cr, uid, 'Sparepart', context)
            domain['product_ids'] = [('categ_id','in',categ_ids)]
        return  {'value':value, 'domain':domain, 'warning':warning}

class ito_report(models.AbstractModel):
    _name = 'report.dym_ito_report.ito_report_template'

    def _get_categ_ids(self, cr, uid, categ_name, context=None):
        obj_categ = self.pool.get('product.category')
        all_categ_ids = obj_categ.search(cr, uid, [])
        categ_ids = obj_categ.get_child_ids(cr, uid, all_categ_ids, categ_name)
        return categ_ids

    def render_html(self, cr, uid, ids, data=None, context=None):
        registry = openerp.registry(cr.dbname)
        branch = ''
        division = ''
        date = False
        first_date = False
        branch_ids = []
        product_ids = []
        domain = [('state','=','done'),'|',('location_id.usage','=','internal'),('location_dest_id.usage','=','internal')]

        check_wizard = registry.get('dym.ito.report').read(cr, uid, ids, context=context)
        if check_wizard:
            data_wizard = check_wizard[0]
            if data_wizard['product_ids']:
                product_ids = data_wizard['product_ids']
                # domain.append(('product_id', 'in', data_wizard['product_ids']))
            elif data_wizard['division'] != False:
                categ_ids = self._get_categ_ids(cr, uid, data_wizard['division'], context)
                product_ids = self.pool.get('product.product').search(cr, uid, [('categ_id','in',categ_ids)], order='name asc')
                # domain.append(('product_id.categ_id', 'in', categ_ids))
                division = data_wizard['division']
            else:
                categ_ids = self._get_categ_ids(cr, uid, 'Unit', context)
                product_ids = self.pool.get('product.product').search(cr, uid, [('categ_id','in',categ_ids)], order='name asc')
                categ_ids = self._get_categ_ids(cr, uid, 'Sparepart', context)
                product_ids += self.pool.get('product.product').search(cr, uid, [('categ_id','in',categ_ids)], order='name asc')
                # domain.append(('product_id.categ_id', 'in', categ_ids))
                division = 'Unit, Sparepart'

            if data_wizard['branch_ids']:
                branch_ids = data_wizard['branch_ids']
                # domain.append(('branch_id', 'in', data_wizard['branch_ids']))
            else:
                branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
                branch_ids = [b.id for b in branch_ids_user]
            for branch_obj in self.pool.get('dym.branch').browse(cr, uid, branch_ids):
                branch += '[' + branch_obj.code + ']' + branch_obj.name + ', '
            if branch != '':
                branch = branch[:-2]

            if data_wizard['date'] != False:
                domain.append(('date', '<=', data_wizard['date']))
                date = data_wizard['date']
                tanggal = datetime.strptime(data_wizard['date'], '%Y-%m-%d').day
                first_date = datetime.strptime(data_wizard['date'], '%Y-%m-%d') - timedelta(days=tanggal-1)
                first_date = first_date.strftime('%Y-%m-%d')
            move_ids = []
            for branch_id in branch_ids:
                for product_id in product_ids:
                    domain_move = []
                    domain_move += domain
                    domain_move.append(('branch_id', '=', branch_id))
                    domain_move.append(('product_id', '=', product_id))
                    move_ids += registry.get('stock.move').search(cr, uid, domain_move, order='date desc, id desc', limit=1, context=None)
            moves_brw = registry.get('stock.move').browse(cr, uid, move_ids, context=context)
            if not moves_brw:
                raise osv.except_osv(('Perhatian !'), ("Data ITO tidak ditemukan."))
        report_obj = self.pool['report']
        report = report_obj._get_report_from_name(cr, uid, 'dym_ito_report.ito_report_template')
        docargs = {'doc_ids': ids,'doc_model': report.model,'docs': data,'branch': branch,'division': division,'date': date,'first_date': first_date,'moves': moves_brw}
        return report_obj.render(cr, uid, ids, 'dym_ito_report.ito_report_template', docargs, context=context)

        