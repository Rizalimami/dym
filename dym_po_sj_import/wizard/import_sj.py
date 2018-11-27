# -*- coding: utf-8 -*-
##############################################################################
#
#    This module copyright (C) 2015 Therp BV (<http://therp.nl>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import base64
from datetime import datetime
from openerp import models, fields, api, _, exceptions
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from openerp.exceptions import Warning as UserError, RedirectWarning

class ImportSuratJalan(models.TransientModel):
    _name = 'import.surat.jalan'

    branch_id = fields.Many2one('dym.branch', string='Branch', required=True)
    ahm_code = fields.Char(string='AHM Code', related='branch_id.ahm_code') 
    partner_id = fields.Many2one(
        'res.partner', string='Supplier',
        help='Supplier name.')
    file_type = fields.Selection([('sj','Surat Jalan (*.sj)'),('do','Delivery Order (*.do)'),('csv','CSV File (*.csv)')], default='sj')
    division = fields.Selection([('Unit','Showroom'),('Sparepart','Workshop')], string='Division')
    data_file = fields.Binary(
        'File', required=True,
        help='File to be imported.')

    @api.multi
    def import_file(self):
        self.ensure_one()
        data_file = base64.decodestring(self.data_file)
        values = {}

        if self.division == 'Unit':
            values['unit_lines'] = []
            for n,line in enumerate(data_file.split('\r\n')):
                if line:
                    kode_tipe_product = ""
                    if self.file_type == "sj":
                        data = line.split(';')
                        kode_tipe_product = data[11]
                    elif self.file_type == "csv":
                        data = line.split(',')

                        if n == 0:
                            if data[0] != 'Nomor Surat Jalan' or \
                                data[1] != 'Tanggal Surat Jalan' or \
                                data[2] != 'Supplier Invoice Number' or \
                                data[3] != 'Supplier Invoice Date' or \
                                data[4] != 'Nomor ND' or \
                                data[5] != 'Nopol Ekspedisi' or \
                                data[6] != 'Engine Number' or \
                                data[7] != 'Chassis Number' or \
                                data[8] != 'Tahun Perakitan' or \
                                data[9] != 'Type Motor' or \
                                data[10] != 'Warna':
                                raise UserError(_("Format header salah, seharusnya: \
                                    Nomor Surat Jalan, \
                                    Tanggal Surat Jalan, \
                                    Supplier Invoice Number, \
                                    Supplier Invoice Date, \
                                    Nomor ND, \
                                    Nopol Ekspedisi, \
                                    Engine Number, \
                                    Chassis Number, \
                                    Tahun Perakitan, \
                                    Type Motor, \
                                    Warna."))
                            continue
                    else:
                        raise Warning(_("Maaf import surat jalan unit hanya mendukung format .csv dan .sj saja."))
                        
                    if "A/T" in data[9]:
                        kode_product = data[9].replace("A/T", " A/T ").strip()
                    elif "M/T" in data[9]:
                        kode_product = data[9].replace("M/T", " M/T ").strip()

                    engine_number = data[6].replace(" ", "").upper()

                    product = self.env['product.product'].search([('name_template', '=', kode_product), ('default_code', '!=', '')], limit=1)

                    values['branch_id'] = self.branch_id.id
                    values['name'] = data[0]
                    values['shipping_date'] = datetime.strptime(data[1],'%d%m%Y').strftime('%Y-%m-%d %H:%M:%S')
                    values['no_faktur'] = data[2]
                    values['faktur_date'] = datetime.strptime(data[3],'%d%m%Y').strftime('%Y-%m-%d %H:%M:%S')
                    values['no_nd'] = data[4]
                    values['division'] = self.division
                    values['state'] = 'draft'
                    values['nopol'] = data[5]
                    values['unit_lines'].append((0,0,{
                        'nomor_surat_jalan': data[0],
                        'tanggal_shipping': datetime.strptime(data[1],'%d%m%Y').strftime('%Y-%m-%d %H:%M:%S'),
                        'no_faktur': data[2],
                        'kode_dealer': data[4],
                        'nama_product': product.default_code,
                        'kode_product': product.name_template,
                        'nomor_mesin': engine_number,
                        'nomor_rangka': data[7],
                        'tahun_perakitan': data[8],
                        'kode_warna': data[10],
                        'kode_tipe_product': kode_tipe_product,
                        'quantity': 1,
                        'sts_receive': False,
                    }))
        elif self.division == 'Sparepart':
            values['part_lines'] = []
            for n,line in enumerate(data_file.split('\r\n')):
                if line:

                    if self.file_type == "csv":
                        data = line.split(',')
                    else:
                        raise Warning(_("Maaf import surat jalan Sparepart hanya mendukung format .csv saja."))

                    if n == 0:
                        if data[0] != 'Nomor Surat Jalan' or \
                            data[1] != 'Tanggal Surat Jalan' or \
                            data[2] != 'Supplier Invoice Number' or \
                            data[3] != 'Supplier Invoice Date' or \
                            data[4] != 'Nopol Ekspedisi' or \
                            data[5] != 'Kode Part' or \
                            data[6] != 'Qty':
                            raise UserError(_("Format header salah, seharusnya: \
                                Nomor Surat Jalan, \
                                Tanggal Surat Jalan, \
                                Supplier Invoice Number, \
                                Supplier Invoice Date, \
                                Nopol Ekspedisi, \
                                Kode Part, \
                                Qty."))
                        continue

                    product = self.env['product.product'].search([('name_template', '=', data[5])])

                    values['branch_id'] = self.branch_id.id
                    values['name'] = data[0]
                    values['shipping_date'] = datetime.strptime(data[1],'%d%m%Y').strftime('%Y-%m-%d %H:%M:%S')
                    values['no_faktur'] = data[2]
                    values['faktur_date'] = datetime.strptime(data[3],'%d%m%Y').strftime('%Y-%m-%d %H:%M:%S')
                    values['division'] = self.division
                    values['state'] = 'draft'
                    values['nopol'] = data[2]
                    values['part_lines'].append((0,0,{
                        'nomor_surat_jalan': data[0],
                        'tanggal_shipping': datetime.strptime(data[1],'%d%m%Y').strftime('%Y-%m-%d %H:%M:%S'),
                        'no_faktur': data[2],
                        'nama_product': product.default_code,
                        'kode_product': product.name_template,
                        'quantity': data[6],
                        'sts_receive': False,
                    }))

        self.env['po.sj.import'].create(values)
