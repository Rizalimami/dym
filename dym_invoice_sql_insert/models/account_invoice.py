import time
import logging

from openerp import SUPERUSER_ID, models, fields, api, _

_logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'


    def sql_insert_account_invoice(self, data):
        cols = data.keys()
        vals = [data[x] for x in cols]
        cols_str = ", ".join(cols)
        vals_str_list = ["%s"] * len(vals)
        vals_str = ", ".join(vals_str_list)
        SQL = "INSERT INTO account_invoice ({cols_str}) VALUES ({vals_str}) RETURNING id".format(cols_str=cols_str, vals_str=vals_str)
        self.env.cr.execute(SQL, vals)
        inv_id = self.env.cr.fetchone()
        print 'Creating Invoice----------------------',cols_str

        return inv_id[0]

    def sql_insert_account_invoice_line(self, data):
        cols = data.keys()
        vals = [data[x] for x in cols]
        cols_str = ", ".join(cols)
        vals_str_list = ["%s"] * len(vals)
        vals_str = ", ".join(vals_str_list)
        SQL = "INSERT INTO account_invoice_line ({cols_str}) VALUES ({vals_str}) RETURNING id".format(cols_str=cols_str, vals_str=vals_str)
        self.env.cr.execute(SQL, vals)
        inv_id = self.env.cr.fetchone()
        return inv_id[0]

    def sql_insert_account_invoice_line_tax(self, data):
        cols = data.keys()
        vals = [data[x] for x in cols]
        cols_str = ", ".join(cols)
        vals_str_list = ["%s"] * len(vals)
        vals_str = ", ".join(vals_str_list)
        SQL = "INSERT INTO account_invoice_line_tax ({cols_str}) VALUES ({vals_str})".format(cols_str=cols_str, vals_str=vals_str)
        self.env.cr.execute(SQL, vals)
        return True

    def sql_insert_account_invoice_wkf_instance(self, invoice_id):
        data = {
            'res_type': 'account.invoice',
            'uid': self.env.user.id,
            'wkf_id': 1,
            'state': 'active',
            'res_id': invoice_id,
        }
        cols = data.keys()
        vals = [data[x] for x in cols]
        cols_str = ", ".join(cols)
        vals_str_list = ["%s"] * len(vals)
        vals_str = ", ".join(vals_str_list)
        SQL = "INSERT INTO wkf_instance ({cols_str}) VALUES ({vals_str}) RETURNING id".format(cols_str=cols_str, vals_str=vals_str)
        self.env.cr.execute(SQL, vals)
        wkf_inst_id = self.env.cr.fetchone()
        return wkf_inst_id[0]

    def sql_insert_account_invoice_wkf_workitem(self, wkf_inst_id):
        data = {
            'act_id': 1,
            'inst_id': wkf_inst_id,
            'state': 'complete',
        }
        cols = data.keys()
        vals = [data[x] for x in cols]
        cols_str = ", ".join(cols)
        vals_str_list = ["%s"] * len(vals)
        vals_str = ", ".join(vals_str_list)
        SQL = "INSERT INTO wkf_workitem ({cols_str}) VALUES ({vals_str}) RETURNING id".format(cols_str=cols_str, vals_str=vals_str)
        self.env.cr.execute(SQL, vals)
        wkf_workitem_id = self.env.cr.fetchone()
        return wkf_workitem_id[0]

    @api.model
    def create(self, vals):
        origin = 'origin' in vals and vals['origin'] or False
        if origin and (origin.startswith("SOR-") or origin.startswith("WOR-")):
            invoice_lines = False
            if 'invoice_line' in vals:
                invoice_lines = vals['invoice_line']
                vals.pop('invoice_line')

            company_id = self._context.get('company_id', self.env.user.company_id.id)
            company = self.env['res.company'].browse(company_id)

            if not 'company_id' in vals:
                vals['company_id'] = company_id

            if not 'currency_id' in vals:
                vals['currency_id'] = company.currency_id.id

            vals['section_id'] = None

            invoice_id = self.sql_insert_account_invoice(vals)
            wkf_inst_id = self.sql_insert_account_invoice_wkf_instance(invoice_id)
            wkf_item_id = self.sql_insert_account_invoice_wkf_workitem(wkf_inst_id)

            for il in invoice_lines:
                inv_line = il[2]
                inv_line['invoice_id'] = invoice_id
                if 'invoice_line_tax_id' in inv_line:
                    new_inv_line = inv_line.copy()
                    new_inv_line.pop('invoice_line_tax_id')
                inv_line_id = self.sql_insert_account_invoice_line(new_inv_line)
                if 'invoice_line_tax_id' in inv_line:
                    tls = inv_line['invoice_line_tax_id']
                    for tl in tls:
                        tax_lines = tl[2]
                        for tax_line in tax_lines:
                            tax_values = {
                                'invoice_line_id': inv_line_id,
                                'tax_id': tax_line,  
                            }
                            self.sql_insert_account_invoice_line_tax(tax_values)
            res = self.env['account.invoice'].browse(invoice_id)
            return res
        else:
            return super(AccountInvoice, self).create(vals)


# >>>>>>>>>>>> account.invoice(883455,)
# >>>>>>>>>>>> account.invoice(883456,)
