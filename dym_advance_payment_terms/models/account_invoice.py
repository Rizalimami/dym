from datetime import datetime, timedelta
from openerp.osv import fields, osv
from openerp import api, _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF

class account_invoice(osv.osv):
    _inherit = "account.invoice"

    # def _fill_due_date(self, cr, uid, ids, document_date, payment_term, context=None):
    #     value = {}
    #     if not document_date:
    #         document_date = fields.date.context_today(self,cr,uid,context=context)
    #     if not payment_term:
    #         # To make sure the invoice due date should contain due date which is
    #         # entered by user when there is no payment term defined
    #         value =  {'date_due': document_date}
    #     if payment_term and document_date:
    #         pterm = self.pool.get('account.payment.term').browse(cr,uid,payment_term)
    #         pterm_list = pterm.compute(value=1, date_ref=document_date)[0]
    #         if pterm_list:
    #             value = {'date_due': max(line[0] for line in pterm_list)}
    #     return value
    
    def onchange_document_date(self, cr, uid, ids, document_date, payment_term, context=None):
        value = self._fill_due_date(cr, uid, ids, document_date, payment_term, context)
        this = self.browse(cr, uid, ids, context=context)
        return {'value': value}


    def onchange_date_due(self, cr, uid, ids, partner_id, date_due, context=None):
        value = {}
        warning = {}
        holiday_name = False
        new_date = False
        Holiday = self.pool.get('hr.holiday.year')
        Partner = self.pool.get('res.partner')

        if not all([partner_id,date_due]):
            return {}

        for partner in Partner.browse(cr, uid, [partner_id], context=context):
            if not partner.advanced_payment_terms:
                return {}

        due_date = datetime.strptime(date_due,DSDF)
        is_holiday = False
        if due_date.weekday()==5:
            is_holiday = True
            holiday_name = 'Sabtu'
        if due_date.weekday()==6:
            is_holiday = True
            holiday_name = 'Minggu'
        holiday_ids = Holiday.search(cr, uid, [('date_start','<=',date_due),('date_stop','>=',date_due)])
        if holiday_ids:
            is_holiday = True
            for holiday in Holiday.browse(cr, uid, holiday_ids, context=context):
                holiday_name = 'libur %s' % holiday.name
        while True:
            due_date_str = due_date.strftime(DSDF)
            holiday_ids = Holiday.search(cr, uid, [('date_start','<=',due_date_str),('date_stop','>=',due_date_str)])
            if due_date.weekday() in (5,6) or holiday_ids:
                due_date = due_date - timedelta(days=1)
            else:
                break
        if is_holiday:
            if due_date.weekday()==0:
                new_duedate_dayname = 'Senin'
            if due_date.weekday()==1:
                new_duedate_dayname = 'Selasa'
            if due_date.weekday()==2:
                new_duedate_dayname = 'Rabu'
            if due_date.weekday()==3:
                new_duedate_dayname = 'Kamis'
            if due_date.weekday()==4:
                new_duedate_dayname = 'Jumat'
            warning = {
                'title': ('Perhatian !'),
                'message': (_('Supplier %s minta agar setiap pembayaran yang jatuh tempo di hari libur pembayarannya dimajukan ke hari kerja. Sedangkan tanggal jatuh tempo %s jatuh di hari %s. Maka dari itu, tanggal jatuh tempo dimajukan ke hari %s yaitu tanggal %s.' % (partner.name, date_due, holiday_name, new_duedate_dayname, due_date_str))),
            }
        value['date_due'] = due_date
        return {'value': value,'warning':warning}