import time
from datetime import datetime
from openerp import models, fields, api
from openerp.osv import osv
from openerp.tools.translate import _

class dym_asset_disposal(models.Model):
    _inherit = 'dym.asset.disposal'
    
    @api.depends('asset_disposal_line')
    def get_qty_asset(self):
        self.qty_asset = len(self.asset_disposal_line)
    
    @api.depends('asset_disposal_line')
    def get_qty_deliver(self):
        deliver_ids = []
        if self.asset_disposal_line:
            deliver_ids = self.env['dym.asset.delivery'].search([('dispose_id','=',self.id)])
        self.deliver_count = len(deliver_ids)

    asset_receive = fields.Boolean('Asset Receive')
    asset_receive_qty = fields.Integer('QTY Asset')
    qty_asset = fields.Integer('Dispose Asset Qty',compute=get_qty_asset)
    deliver_count = fields.Integer('Receiving Assets',compute=get_qty_deliver)
            
    @api.cr_uid_ids_context
    def view_delivery(self,cr,uid,ids,context=None):
        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        dummy, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'dym_asset_disposal', 'deliver_asset_action'))
        action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, context=context)
        obj_delivery = self.pool.get('dym.asset.delivery')
        val = self.browse(cr, uid, ids)
        dispose_ids = obj_delivery.search(cr,uid,[('dispose_id','=',val.id)])
        action['context'] = {}
        if len(dispose_ids) > 1:
            action['domain'] = "[('id','in',[" + ','.join(map(str, dispose_ids)) + "])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'dym_asset_disposal', 'dym_asset_delivery_form_view')
            action['views'] = [(res and res[1] or False, 'form')]
            action['res_id'] = dispose_ids and dispose_ids[0] or False 
        return action

class dym_purchase_order_line(models.Model):
    _inherit = 'purchase.order.line'
    
    delivered = fields.Boolean('Delivered')

class dym_asset_delivery(models.Model):
    _name = 'dym.asset.delivery'
    _description = 'Asset Delivery Order'

    STATE_SELECTION = [
        ('draft', 'Draft'),
        ('done','Posted'),
        ('cancel','Cancelled')
    ]

    name = fields.Char(string="Delivery Asset No", default="#")
    dispose_id = fields.Many2one('dym.asset.disposal',string="Reference")
    date = fields.Date(string="Date",default=fields.Date.context_today)
    delivery_line_ids = fields.One2many('dym.asset.delivery.line','delivery_id')
    state = fields.Selection(STATE_SELECTION, string='State', readonly=True,default='draft')
    branch_id = fields.Many2one(related="dispose_id.branch_id",string='Branch')
    confirm_uid = fields.Many2one('res.users',string="Posted by")
    confirm_date = fields.Datetime('Posted on')
    cancel_uid = fields.Many2one('res.users',string="Cancelled by")
    cancel_date = fields.Datetime('Cancelled on')
    picking_type_id = fields.Many2one('stock.picking.type',string="Picking Type",domain="[('branch_id','!=',False),('branch_id','=',branch_id),('code','=','internal')]", readonly=True)
      

    def _get_default_location_delivery_sales(self,cr,uid,dispose_id,context=None):
        default_location_id = {}
        obj_picking_type = self.pool.get('stock.picking.type')
        for val in self.pool.get('dym.asset.disposal').browse(cr,uid,dispose_id):
            picking_type_id = obj_picking_type.search(cr,uid,[
                                                              ('branch_id','=',val.branch_id.id),
                                                              ('code','=','outgoing')
                                                              ])
            
           
            if picking_type_id:
                for pick_type in obj_picking_type.browse(cr,uid,picking_type_id[0]):
                    if not pick_type.default_location_dest_id.id :
                         raise osv.except_osv(('Perhatian !'), ("Location destination Belum di Setting"))
                    default_location_id.update({
                        'picking_type_id':pick_type.id,
                        'location_dest_id': pick_type.default_location_dest_id.id,
                    })
            else:
               raise osv.except_osv(('Error !'), ('Tidak ditemukan default lokasi untuk penjualan di konfigurasi cabang \'%s\'!') % (val.branch_id.name,)) 
        return default_location_id

    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(dym_asset_delivery, self).default_get(cr, uid, fields, context=context)
        dispose_ids = context.get('active_ids', [])
        active_model = context.get('active_model')
        if not dispose_ids or len(dispose_ids) != 1 or not context.get('active_model') or 'dym.asset.disposal' not in context.get('active_model'):
            return res
        assert active_model in ('dym.asset.disposal'), 'Bad context propagation'
        dispose_id = dispose_ids
        dispose = self.pool.get('dym.asset.disposal').browse(cr, uid, dispose_id, context=context)
        items = []
        location = self._get_default_location_delivery_sales(cr, uid, dispose_id, context=context)
        for op in dispose.asset_disposal_line:
            if op.delivered == False:
                location_dest_id = False
                if dispose.amount_total > 0:
                    location_dest_id = location['location_dest_id']
                else:
                    scrap_location = self.pool.get('stock.location').search(cr, uid, [('scrap_location','=',True),('branch_id','=',dispose.branch_id.id)], limit=1)
                    if not scrap_location:
                        raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan lokasi scrap di branch %s!")%(dispose.branch_id.name))
                    location_dest_id = scrap_location[0]
                item = {
                    'dispose_line_id': op.id,
                    'asset_id': op.asset_id.id,
                    'price_unit': op.amount,
                    'description': op.description,
                    'location_id': op.asset_id.location_id.id,
                    'location_dest_id': location_dest_id,
                }
                items.append(item)
        res.update(delivery_line_ids=items)
        res.update(picking_type_id=location['picking_type_id'])
        res.update(dispose_id=dispose_id[0])
        return res

    @api.multi
    def deliver(self) :
        dispose = self.dispose_id
        for x in self.delivery_line_ids:
            if dispose.amount_total > 0:
                x.asset_id.write({'location_id':x.location_dest_id.id,'state':'sold'})
                update_vals = {'location_id':x.location_dest_id.id,'state':'sold'}
            else:
                x.asset_id.write({'location_id':x.location_dest_id.id,'state':'scrap'})
                update_vals = {'location_id':x.location_dest_id.id,'state':'scrap'}
            # x.asset_id.update_asset(x.asset_id.child_ids, update_vals)
            x.dispose_line_id.write({'delivered':True})
        asset_receive_qty =  dispose.asset_receive_qty + len(self.delivery_line_ids)
        dispose.write({'asset_receive_qty':asset_receive_qty})    
        if dispose.asset_receive_qty == dispose.qty_asset :
            if dispose.invoiced == True:
                dispose.write({'asset_receive':True, 'state':'done'})
            else:
                dispose.write({'asset_receive':True})
            delivery_cancel = self.search([('dispose_id','=',dispose.id),('state','=','draft')])
            delivery_cancel.write({'state':'cancel','cancel_uid':self._uid,'cancel_date':datetime.now()})

        self.write({'date':datetime.today(),'state':'done','confirm_uid':self._uid,'confirm_date':datetime.now()})
        return True
    
                
    @api.model
    def create(self,values,context=None):
        vals = []
        values['name'] = '/' 
        # values['name'] = self.env['ir.sequence'].get_sequence('DELA')     
        deliver_asset = super(dym_asset_delivery,self).create(values)  
        name = self.env['ir.sequence'].get_per_branch(deliver_asset.dispose_id.branch_id.id, 'DAS', division='Umum') 
        deliver_asset.write({'name':name})        
        return deliver_asset
        
    @api.multi
    def onchange_dispose(self,dispose_id):
        if dispose_id :
            items = []
            dispose_obj = self.env['dym.asset.disposal'].browse([dispose_id])
            rekap_asset = {}
            location = self._get_default_location_delivery_sales(dispose_id)
            for op in dispose_obj.asset_disposal_line :
                if op.delivered == False:
                    location_dest_id = False
                    if dispose_obj.amount_total > 0:
                        location_dest_id = location['location_dest_id']
                    else:
                        scrap_location = self.env['stock.location'].search([('scrap_location','=',True),('branch_id','=',dispose_obj.branch_id.id)], limit=1)
                        if not scrap_location:
                            raise osv.except_osv(('Perhatian !'), ("Tidak ditemukan lokasi scrap di branch %s!")%(dispose_obj.branch_id.name))
                        location_dest_id = scrap_location.id
                    items.append([0,0,{
                        'dispose_line_id': op.id,
                        'asset_id': op.asset_id.id,
                        'price_unit': op.amount,
                        'description': op.description,
                        'location_id': op.asset_id.location_id.id,
                        'location_dest_id': location_dest_id,
                    }])
            return {'value':{'delivery_line_ids': items,'picking_type_id': location['picking_type_id']}}
            
    @api.cr_uid_ids_context
    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(('Perhatian !'), ("Delivery Asset %s tidak bisa dihapus dalam status 'Posted' atau 'Cancel' !")%(item.name))
        return super(dym_asset_delivery, self).unlink(cr, uid, ids, context=context)     

class dym_asset_delivery_line(models.Model):
    _name = 'dym.asset.delivery.line'
    _rec_name = 'description'
    
        
    delivery_id = fields.Many2one('dym.asset.delivery',string="Delivery No")
    asset_id = fields.Many2one('account.asset.asset',string="Asset", readonly=True)
    description = fields.Char(string='Description')
    dispose_line_id = fields.Many2one('dym.asset.disposal.line') 
    price_unit = fields.Float('Price Unit', readonly=True)
    location_id = fields.Many2one('stock.location',string="Source Location",domain="[('branch_id','!=',False),('branch_id','=',branch_id),('usage','=','internal')]", readonly=True)
    location_dest_id = fields.Many2one('stock.location',string="Destination Location",domain="[('branch_id','!=',False),('branch_id','=',branch_id),('usage','=','internal')]", readonly=True)