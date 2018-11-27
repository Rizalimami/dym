from openerp.osv import fields, osv, orm
from openerp.tools.translate import _

class dym_reclass_payment(osv.osv_memory):
    _name = "dym.reclass.payment"
    _description = "Reclass Unidentified Payment"
        
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Customer', domain=['|','|',('customer','=',True),('direct_customer','=',True),('is_group_customer','=',True)], required=True),
        'division':fields.selection([('Unit','Showroom'),('Sparepart','Workshop'),('Umum','General'),('Finance','Finance')], 'Division', change_default=True, select=True),
        'old_date': fields.date(string='Old Date'),
        'old_account_id': fields.many2one('account.account', string='Old Account'),
        'new_date': fields.date(string='New Date'),
        'new_account_id': fields.many2one('account.account', string='New Account'),
    }

    _defaults = {
        'new_date': fields.date.context_today,
    }
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        if context and context.get('active_ids', False):
            if len(context.get('active_ids')) > 1:
                raise osv.except_osv(_('Warning!'), _("You may only process one payment at a time!"))
        res = super(dym_reclass_payment, self).default_get(cr, uid, fields, context=context)
        payment_id = context and context.get('active_id', False) or False
        payment = self.pool.get('account.voucher').browse(cr, uid, payment_id, context=context)

        partner_id = payment.partner_id.id
        division = payment.division

        line_cr_id = False
        if payment.line_cr_ids:
            line_cr_id = payment.line_cr_ids[0]

        if 'partner_id' in fields:
            res.update({'partner_id': partner_id})
        if 'division' in fields:
            res.update({'division': division})
        if 'old_date' in fields:
            res.update({'old_date': payment.date})
        if 'old_account_id' in fields:
            res.update({'old_account_id': line_cr_id and line_cr_id.account_id.id})
        return res

    def _get_period(self, cr, uid, context=None):
        ctx = dict(context or {})
        voucher_obj = self.pool.get('account.voucher')
        voucher = voucher_obj.browse(cr, uid, context.get('active_ids'),context=context)
        period_id = self.pool.get('account.period').search(cr, uid, [('company_id','=',voucher.company_id.id)], context=ctx)
        return period_id[0]

    def action_move_create(self, cr, uid, ids, context=None):
        res = {}
        val = self.browse(cr,uid,ids)
        voucher_obj = self.pool.get('account.voucher')
        voucher = voucher_obj.browse(cr, uid, context.get('active_ids'),context=context)
        prefix = voucher.journal_id.code
        move = self.pool.get('account.move')

        if not voucher.number:
            raise osv.except_osv(_('Error!'),_("Voucher ini tidak memiliki nomor."))

        # period_id = self._get_period(cr, uid, context=context)
        period_id = self.pool.get('account.period').find(cr, uid, val.new_date, context=context)
        if not period_id:
            raise osv.except_osv(_('Error!'),_("Tidak ditemukan account period untuk tanggal %s." % val.new_date))
        period_id = period_id[0]
        name = (voucher.number or '/') + ' (reclass)'
        ref = (voucher.reference or '/') + ' (reclass)'

        amount = 0.0
        for move_line in voucher.move_ids:
            if move_line.account_id.id == val.old_account_id.id:
                amount = move_line.credit
                analytic_account_id = move_line.analytic_account_id

        move_line_db = {
            'name':name,
            'ref':name,
            'partner_id': val.partner_id.id,
            'account_id': val.old_account_id.id,
            'journal_id': voucher.journal_id.id,
            'period_id': period_id,
            'date': val.new_date,
            'debit': amount,
            'credit': 0.0,
            'branch_id' : voucher.branch_id.id,
            'division' : voucher.division,
            'analytic_account_id' : analytic_account_id.id,
        }
        move_line_cr = {
            'name':name,
            'ref':name,
            'partner_id': val.partner_id.id,
            'account_id': val.new_account_id.id,
            'journal_id': voucher.journal_id.id,
            'period_id': period_id,
            'date': val.new_date,
            'debit': 0.0,
            'credit': amount,
            'branch_id' : voucher.branch_id.id,
            'division' : voucher.division,
            'analytic_account_id' : analytic_account_id.id,
        }
        reclass_move = {
            'name': name,
            'ref': name,
            'journal_id': voucher.journal_id.id,
            'date': val.new_date,
            'period_id':period_id,
            'transaction_id': voucher.id,
            'model':voucher.__class__.__name__,
            'line_id': [
                (0,0,move_line_db),
                (0,0,move_line_cr),
            ]
        }
        reclass_move = move.create(cr, uid, reclass_move, context=context)
        return reclass_move

    def reclass_payment(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        voucher_obj = self.pool.get('account.voucher')
        data = self.browse(cr, uid, ids, context=None)
        voucher = voucher_obj.browse(cr, uid, context.get('active_ids'),context=context)
        partner_id = data.partner_id.id
        division = data.division

        if not voucher.line_cr_ids:
            raise osv.except_osv(_('Error!'),_("Voucher tidak memiliki jurnal."))

        move_reclass_id = self.action_move_create(cr, uid, ids, context=context)

        vals = {
            'partner_id':partner_id,
            'division':division,
            'unidentified_payment':False,
            'move_reclass_id': move_reclass_id,
        }
        voucher_obj.write(cr, uid, context.get('active_ids'), vals, context=None)
        return True