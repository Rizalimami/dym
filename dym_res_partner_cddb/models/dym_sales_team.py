from openerp import models, fields, api, _
from openerp.osv import osv

class CRMCaseSection(models.Model):
    _inherit = "crm.case.section"
             
    employee_id = fields.Many2one('hr.employee', string='Team Leader Employee')
    member_ids = fields.Many2many('hr.employee', 'sale_member_empl_rel', 'section_id', 'member_id', 'Team Members')
    branch_id = fields.Many2one('dym.branch', related="user_id.branch_id", string='Branch', required=False, store=True)
    company_id = fields.Many2one('res.company', related="branch_id.company_id")

    @api.onchange('user_id')
    def change_user_id(self):
        if not self.user_id:
            return False
        fields_list = ['user_id']
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        employee = self.env['hr.employee'].search([('user_id','=',self.user_id.id)], limit=1)
        values = dict.fromkeys(fields_list, False)
        if not employee:
            self.user_id = []
            self.employee_id = []
            return {
                'warning': {
                        'title': _('Error!'), 
                        'message': _("x1 I could not find that user %s is related to an employee or may be he/she has not registered as an employee yet. If he/she is registered as an employee, then please relate him/her in field 'Related User' in employee form (Human Resources > Employee). If you are not able to do it, please contact system administrator." % self.user_id.name)
                    }, 
                'value': values
            }
        if employee and not employee.company_id:
            self.user_id = []
            self.employee_id = []
            return {
                'warning': {
                        'title': _('Error!'), 
                        'message': _("x2 I found that user %s is registered as an employee but I could not find which company is he/she is working for. To correct this issue, please go to menu Human Resources > Employee, click tab Public Information and select %s at the Company field. Please contact system administrator to correct this issue." % (self.user_id.name, self.env.user.company_id.name))
                    }, 
                'value': values
            }
        if employee and employee.company_id.id != company_id:            
            self.user_id = []
            self.employee_id = []
            return {
                'warning': {
                        'title': _('Error!'), 
                        'message': _("x3 I found that user %s is registered as an employee for the company %s and not for %s. Please contact system administrator to correct this issue." % (self.user_id.name, employee.company_id.name, self.env.user.company_id.name))
                    }, 
                'value': values
            }
        self.employee_id = employee[0].id

    @api.onchange('employee_id')
    def change_employee_id(self):
        if not self.employee_id:
            return False
        fields_list = ['employee_id']
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        values = dict.fromkeys(fields_list, False)
        if not self.employee_id.user_id:
            self.user_id = []
            self.employee_id = []
            return {
                'warning': {
                        'title': _('Error!'), 
                        'message': _("I could not find that employee %s is related to any user yet. Please relate him/her in field 'Related User' in employee form (Human Resources > Employee). If you are not able to do it, please contact system administrator." % self.user_id.name)
                    }, 
                'value': values
            }
        self.user_id = self.employee_id.user_id.id
