# -*- coding: utf-8 -*-
from openerp import fields, models, api, _
from openerp.exceptions import Warning
import openerp.addons.decimal_precision as dp
from datetime import datetime, date, timedelta
import logging
_logger = logging.getLogger(__name__)

class udstk_partner(models.Model):
    _inherit = "res.partner"

    def is_udstk_ok(self,val):
        '''        
        if val.street_tab :
            if val.rt_tab :
                if val.rw_tab :
                    if val.state_tab_id :
                        if val.city_tab_id :
                            if val.kecamatan_tab_id :
                                if val.zip_tab_id :
                                    if val.kelurahan_tab :
                                        return True
        else :
            return False
        '''
        return True

    @api.multi
    def write(self, vals):
        
        # res.partner must only allow to set the company_id of a partner if it
        # is the same as the company of all users that inherit from this partner
        # (this is to allow the code from res_users to write to the partner!) or
        # if setting the company_id to False (this is compatible with any user
        # company)
        for partner in self:

            lot = self.env['stock.production.lot']
            lot_search = lot.search([
                                    ('customer_stnk','=',partner.id),
                                    ('lot_status_cddb','!=','ok'),
                                    ('state_stnk','=',False),'|',
                                    ('state','=','paid'),'|',
                                    ('state','=','sold'),'|',
                                    ('state','=','paid_offtr'),
                                    ('state','=','sold_offtr')
                                ])

            if lot_search:
                lot_browse = lot.browse(lot_search)
                is_udstk_ok = self.is_udstk_ok(vals)
                if is_udstk_ok :
                    for x in lot_browse :
                        if x.lot_status_cddb == 'cddb' :
                            lot_browse.write({'lot_status_cddb':'ok'})
                        if x.lot_status_cddb == 'ok' :
                            lot_browse.write({'lot_status_cddb':'ok'})
                        if x.lot_status_cddb == 'not' :
                            lot_browse.write({'lot_status_cddb':'udstk'})

        result = super(udstk_partner, self).write(vals)
        return result
