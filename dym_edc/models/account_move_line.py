# -- coding: utf-8 --
import time
from datetime import datetime

from openerp import api, workflow
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp import tools
from openerp.report import report_sxw
import openerp

class account_move_line(osv.osv):
    _inherit = "account.move.line"

    @api.constrains('reconcile_id', 'reconcile_partial_id')
    def _check_reconcile_same_partner(self):
        """ Ensure the partner is the same or empty on all lines and a reconcile mark.
            We allow that only for opening/closing period"""
        for line in self:
            rec = False
            move_lines = []
            if line.reconcile_id:
                rec = line.reconcile_id
                move_lines = rec.line_id
            elif line.reconcile_partial_id:
                rec = line.reconcile_partial_id
                move_lines = rec.line_partial_ids
            if self.journal_id.type=='edc':
                continue
            if rec and not rec.opening_reconciliation:
                first_partner = line.partner_id
                for rline in move_lines:
                    if (rline.partner_id != first_partner and
                            rline.account_id.type in ('receivable', 'payable')):
                        raise osv.except_osv(
                                _('Error!'), _("You can only reconcile journal items with the same partner."))