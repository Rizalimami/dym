from openerp.osv import osv, fields, orm
from openerp.tools.translate import _

class dym_purchase_order(osv.osv):
    _inherit = 'purchase.order'

    def onchange_picking_type_id(self, cr, uid, ids, id_branch, id_picking_type, change_branch=False, asset=False, prepaid=False, order_line=False, purchase_order_type_id=False, context=None):
        res = super(dym_purchase_order, self).onchange_picking_type_id(cr, uid, ids, id_branch, id_picking_type, change_branch=change_branch, asset=asset, prepaid=prepaid, order_line=order_line, purchase_order_type_id=purchase_order_type_id, context=context)
        value = {}
        warning = {}
        dom = {}
        value['picking_type_id'] = False

        this = self.browse(cr, uid, ids, context=context)
        branch_id = self.pool.get('dym.branch').browse(cr, uid, id_branch)

        obj_picking_type = self.pool.get('stock.picking.type')
        picking_type_ids = obj_picking_type.search(cr, uid, [
            ('code','=','incoming'),
            ('branch_id','=',id_branch)
        ])        
        if change_branch == True and id_branch:
            analytic_1, analytic_2, analytic_3, analytic_4 = self.get_analytic_combi(cr, uid, id_branch, asset, prepaid, order_line, purchase_order_type_id)
            if analytic_1:
                value['analytic_1'] = analytic_1
            value['analytic_2'] = analytic_2
            value['analytic_3'] = analytic_3
            value['analytic_4'] = analytic_4
        id_picking_type = False
        if picking_type_ids :
            id_picking_type = picking_type_ids[0]
        if id_branch :
            if branch_id.branch_status in ['H1','H123']:
                value['partner_id']=branch_id.default_supplier_id.id
            if branch_id.branch_status in ['H23']:
                value['partner_id']=branch_id.default_supplier_workshop_id.id
            partner_type_id = self.pool.get('dym.partner.type').search(cr, uid, [('name','=','principle')])
            dom['partner_type'] = "['|',('division','like',division),('id','=',"+str(partner_type_id[0])+")]"
            value['partner_type']= int(partner_type_id[0])
            if id_picking_type :
                value['picking_type_id'] = id_picking_type
            else :
                warning = {"title":"Perhatian", "message":"Tidak ditemukan type picking 'Receipts' untuk '%s'\nsilahkan buat di menu Warehouse > Type Of Operation" %branch_id.name}
                value['picking_type_id'] = False
                value['branch_id'] = False
        if id_picking_type :
            picktype = self.pool.get("stock.picking.type").browse(cr, uid, [id_picking_type])
            if picktype.default_location_dest_id :
                value.update({'location_id': picktype.default_location_dest_id.id})
            value.update({'related_location_id': picktype.default_location_dest_id and picktype.default_location_dest_id.id or False})
        

        return {'value': value, 'warning':warning, 'domain':dom}
