from openerp.osv import fields, osv

class dym_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'incentive_finco_ids': fields.one2many('dym.incentive.finco.line','partner_id',string='Subsidi'),
    }
