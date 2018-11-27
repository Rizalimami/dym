from openerp import models, fields, api, _
from datetime import datetime, timedelta
import calendar

class dym_purchase_order_type(models.Model):
    _name = "dym.purchase.order.type"

    name = fields.Char()
    category = fields.Selection([
            ('Unit','Showroom'),
            ('Sparepart','Workshop'),
            ('Umum','General'),
        ], string='Type')
    date_start = fields.Selection([
            ('now','Now'),
            ('end_of_month','End of Month'),
            ('next_month', 'Beginning of Next Month'),
            ('end_of_next_month','End of Next Month'),
            ('next_2_months','Beginning of Next two Months'),
            ('end_of_next_2_months', 'End of Next two Months'),
        ], string='Start Date')
    date_end = fields.Selection([
            ('now','Now'),
            ('end_of_month','End of Month'),
            ('next_month', 'Beginning of Next Month'),
            ('end_of_next_month','End of Next Month'),
            ('next_2_months','Beginning of Next two Months'),
            ('end_of_next_2_months', 'End of Next two Months'),
        ], string='End Date')
    invoice_method = fields.Selection([('manual','Based on Purchase Order lines'),('order','Based on generated draft invoice'),('picking','Based on incoming shipments')], string='Invoicing Control', help="Based on Purchase Order lines: place individual lines in 'Invoice Control / On Purchase Order lines' from where you can selectively create an invoice.\n Based on generated invoice: create a draft invoice you can validate later.\n Based on incoming shipments: let you create an invoice when receipts are validated.")
    mandatory_so_wo = fields.Boolean('Mandatory SO/WO')
    mandatory_hutang_lain = fields.Boolean('Mandatory Customer Deposit')
    editable_price = fields.Boolean('Editable Price')

    _sql_constraints = [
        ('config_categ_potype_uniq', 'unique(category, name)', 'PO Type must be unique per category!')
    ]

    def get_date(self,date_type) :
        now = datetime.today()
        
        bulan_next1 = now.month+1-12 if now.month+1>12 else now.month+1
        bulan_next2 = now.month+2-12 if now.month+2>12 else now.month+2
        tahun = now.year+1 if now.month+1>12 else now.year
        
        if date_type == 'now':
            return now
        elif date_type == 'end_of_month':
            return datetime(now.year, now.month, calendar.monthrange(now.year,now.month)[1])
        elif date_type == 'next_month':
            return datetime(tahun, bulan_next1, 1)
        elif date_type == 'end_of_next_month':
            return datetime(tahun, bulan_next1, calendar.monthrange(tahun,bulan_next1)[1])
        elif date_type == 'next_2_months':
            return datetime(tahun, bulan_next2, 1)
        elif date_type == 'end_of_next_2_months':
            return datetime(tahun, bulan_next2, calendar.monthrange(tahun,bulan_next2)[1])
        
        return now
        
