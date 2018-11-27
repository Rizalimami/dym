from openerp.osv import fields, osv, orm
import openerp.addons.decimal_precision as dp
from datetime import datetime
from openerp.tools.translate import _
from openerp import tools
from lxml import etree

class dym_writeoff_confirmation(osv.osv_memory):
    _name = "dym.writeoff.confirmation"

    