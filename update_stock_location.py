#!/bin/python

import csv
import erppeek
from glob import glob
from datetime import datetime

#file = 'STM_INVOICE_REGULER.csv'
#file = 'OPBAL/AP/%s' % file

# ----------------------------------------------------------------
host = 'localhost'
port = '8069'
admin_pw = '1'
dbname = 'odm'

client = erppeek.Client('http://%s:%s' % (host, port))
client.login('admin', admin_pw, dbname)


print "1. Check parent_left dan parent_right SEBELUM update ...................."

loc_ids = client.model('stock.location').search([('company_id','=',3)],limit=100)
locs = client.model('stock.location').read(loc_ids,['parent_left','parent_right','name'])
for loc in locs:
	print "parent_left=",loc['parent_left'], " parent_left=",loc['parent_right'], " loc name=",loc['name']




print "2. Tunggu, proses update parent_left dan parent_right ...................."

loc_ids = client.model('stock.location').search([('company_id','=',3)], limit=2)
locs = client.model('stock.location').browse(loc_ids)
for loc in locs:
	client.model('stock.location').parent_store_compute()



print "3. Check parent_left dan parent_right SETELAH update ...................."

loc_ids = client.model('stock.location').search([('company_id','=',3)],limit=100)
locs = client.model('stock.location').read(loc_ids,['parent_left','parent_right','name'])
for loc in locs:
	print "parent_left=",loc['parent_left'], " parent_left=",loc['parent_right'], " loc name=",loc['name']
