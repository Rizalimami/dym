import time
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp import SUPERUSER_ID
from lxml import etree

class dym_product_product(models.Model):
    _inherit = 'product.product'

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        result = []
        recs = self.browse()
        if name and len(name) >= 3:
            recs = self.search([('number', '=', name)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        for prod in recs:
            result.append((prod.id, "%s [%s]" % (prod.name, prod.default_code)))
        return result

    @api.one
    def _compute_stock(self):
        self.stock_intransit = '-'
        self.stock_rfs = '-'
        self.stock_nrfs = '-'
        self.stock_reserved = '-'
        self.stock_undelivered = '-'
        self.stock_transferred = '-'
        context = self._context
        # if ('location_id' in context and context['location_id']) or ('branch_id' in context and context['branch_id']) and self.categ_id.get_root_name() != 'Service':
        branch_id = False
        if 'branch_id' in context and context['branch_id']:
            branch_id = context['branch_id']
        else:
            user = self.env['res.users'].browse(self._uid)
            if len(user.area_id.branch_ids) == 1:
                branch_id = user.area_id.branch_ids[0].id
        if  branch_id and self.categ_id.get_root_name() != 'Service':
            intransit_domain_unit = [('location_id.usage','in',['internal','nrfs','kpb']),('lot_id.state','=','intransit'),('product_id','=',self.id)]
            intransit_domain_non_unit = [('location_id.usage','in',['internal','nrfs','kpb']),('product_id','=',self.id),('consolidated_date','=',False)]
            rfs_domain_unit = [('location_id.usage','=','internal'),('lot_id.state','=','stock'),('product_id','=',self.id),('reservation_id','=',False)]
            rfs_domain_non_unit = [('location_id.usage','=','internal'),('product_id','=',self.id),('consolidated_date','!=',False),('reservation_id','=',False)]
            nrfs_domain_unit = [('location_id.usage','in',['nrfs','kpb']),('lot_id.state','=','stock'),('product_id','=',self.id),('reservation_id','=',False)]
            nrfs_domain_non_unit = [('location_id.usage','in',['nrfs','kpb']),('product_id','=',self.id),('consolidated_date','!=',False),('reservation_id','=',False)]
            reserved_domain_unit = [('location_id.usage','in',['internal','nrfs','kpb']),('product_id','=',self.id),'|',('lot_id.state','=','reserved'),'&',('reservation_id','!=',False),('lot_id.state','not in',['sold','sold_offtr','paid','paid_offtr'])]
            # reserved_domain_non_unit = [('location_id.usage','in',['internal','nrfs']),('product_id','=',self.id),('reservation_id','!=',False)]
            undelivered_domain_unit = [('location_id.usage','in',['internal','nrfs','kpb']),('lot_id.state','in',['sold','sold_offtr','paid','paid_offtr']),('product_id','=',self.id),('reservation_id','!=',False)]
            undelivered_domain_non_unit = [('location_id.usage','in',['internal','nrfs','kpb']),('product_id','=',self.id),('reservation_id','!=',False)]
            transferred_domain_unit = [('location_id.usage','=','customer'),('lot_id.state','in',['sold','sold_offtr','paid','paid_offtr']),('product_id','=',self.id),('reservation_id','=',False)]
            transferred_domain_non_unit = [('location_id.usage','=','customer'),('product_id','=',self.id),('reservation_id','=',False)]
            domain_location = []
            domain_location_per_branch = []
            # if 'location_id' in context and context['location_id']:
            #     domain_location = [('location_id','=',context['location_id'])]
            if branch_id:
                location_ids = self.env['stock.location'].search([('branch_id','=',branch_id)])
                if location_ids:
                    domain_location_per_branch = [('location_id','in',location_ids.ids)]
            intransit_domain_unit += domain_location_per_branch
            intransit_domain_non_unit += domain_location_per_branch
            rfs_domain_unit += domain_location_per_branch
            rfs_domain_non_unit += domain_location_per_branch
            nrfs_domain_unit += domain_location_per_branch
            nrfs_domain_non_unit += domain_location_per_branch
            reserved_domain_unit += domain_location_per_branch
            # reserved_domain_non_unit += domain_location
            undelivered_domain_unit += domain_location_per_branch
            undelivered_domain_non_unit += domain_location_per_branch
            transferred_domain_unit += domain_location_per_branch
            transferred_domain_non_unit += domain_location_per_branch
            if self.categ_id.isParentName('Unit'):
                intransit_quant = self.env['stock.quant'].search(intransit_domain_unit)
                self.stock_intransit = sum(quant.qty for quant in intransit_quant) 

                rfs_quant = self.env['stock.quant'].search(rfs_domain_unit)
                self.stock_rfs = sum(quant.qty for quant in rfs_quant) 

                nrfs_quant = self.env['stock.quant'].search(nrfs_domain_unit)
                self.stock_nrfs = sum(quant.qty for quant in nrfs_quant) 

                reserved_quant = self.env['stock.quant'].search(reserved_domain_unit)
                self.stock_reserved = sum(quant.qty for quant in reserved_quant) 

                undelivered_quant = self.env['stock.quant'].search(undelivered_domain_unit)
                self.stock_undelivered = sum(quant.qty for quant in undelivered_quant) 

                transferred_quant = self.env['stock.quant'].search(transferred_domain_unit)
                self.stock_transferred = sum(quant.qty for quant in transferred_quant) 
            else:
                intransit_quant = self.env['stock.quant'].search(intransit_domain_non_unit)
                self.stock_intransit = sum(quant.qty for quant in intransit_quant) 

                rfs_quant = self.env['stock.quant'].search(rfs_domain_non_unit)
                self.stock_rfs = sum(quant.qty for quant in rfs_quant) 

                nrfs_quant = self.env['stock.quant'].search(nrfs_domain_non_unit)
                self.stock_nrfs = sum(quant.qty for quant in nrfs_quant) 

                # reserved_quant = self.env['stock.quant'].search(reserved_domain_unit)
                self.stock_reserved = '-'

                undelivered_quant = self.env['stock.quant'].search(undelivered_domain_non_unit)
                self.stock_undelivered = sum(quant.qty for quant in undelivered_quant) 

                transferred_quant = self.env['stock.quant'].search(transferred_domain_non_unit)
                self.stock_transferred = sum(quant.qty for quant in transferred_quant) 

    default_code = fields.Char(string='Internal Reference')
    stock_intransit = fields.Char(string='Intransit', compute='_compute_stock')
    stock_rfs = fields.Char(string='Ready for Sale', compute='_compute_stock')
    stock_nrfs = fields.Char(string='Not Ready for Sale', compute='_compute_stock')
    stock_reserved = fields.Char(string='Reserved', compute='_compute_stock')
    stock_undelivered = fields.Char(string='Undelivered', compute='_compute_stock')
    stock_transferred = fields.Char(string='Transferred', compute='_compute_stock')

