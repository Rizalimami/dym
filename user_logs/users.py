from openerp.osv import fields, osv
import datetime
from openerp.http import request
import logging

from openerp.http import root
from openerp.http import request

from os import utime
from os.path import getmtime
from time import time
from openerp import http

_logger = logging.getLogger('======User Logs===')



class res_users(osv.osv):
    _inherit='res.users'
    _description = "User Logs"
    _columns = {
        'user_log_ids': fields.one2many('res.users.log','user_id','User Logs'),
    }

    def authenticate(self, db, login, password, user_agent_env):
        uid = super(res_users, self).authenticate(db, login, password, user_agent_env)
        if uid:
            sign_in = datetime.datetime.now()
            cr = self.pool.cursor()
            session_id=False
            try:
                session_id = request.session_id
                self.pool.get('res.users.log').create(cr, uid,{'user_id':uid,
                                                               'sign_in':sign_in,
                                                               'session_id':session_id})
                cr.commit()
                cr.close()
            except Exception,e:
                cr.close()
                _logger.info("Exception======%s",e)
        return uid

    def _check_session_validity(self, db, uid, passwd):
        if not request:
            return
        session = request.session
        session_store = root.session_store
        param_obj = self.pool['ir.config_parameter']
        delay, urls = param_obj.get_session_parameters(db)
        deadline = time() - delay
        path = session_store.get_session_filename(session.sid)
        try:
            if getmtime(path) < deadline:
                if session.db and session.uid:
                    cr = self.pool.cursor()
                    log_pool = self.pool.get('res.users.log')
                    sign_out = datetime.datetime.now()
                    session_id = request.session_id
                    log_id = log_pool.search(cr, uid, [('session_id','=',session_id)])
                    log_pool.write(cr,uid,log_id,{'sign_out':sign_out})
                    cr.commit()
                    cr.close()
                    session.logout(keep_db=True)
            elif http.request.httprequest.path not in urls:
                # the session is not expired, update the last modification
                # and access time.
                utime(path, None)
        except OSError:
            pass
        return


    def check(self, db, uid, passwd):
        res=super(res_users, self).check(db, uid, passwd)
        self._check_session_validity(db, uid, passwd)
        try:
            req = request.httprequest
            base_url = req.base_url
            if base_url.split('/')[-1] == 'logout':
                cr = self.pool.cursor()
                log_pool = self.pool.get('res.users.log')
                sign_out = datetime.datetime.now()
                session_id = request.session_id
                log_id = log_pool.search(cr, uid, [('session_id','=',session_id)])
                log_pool.write(cr,uid,log_id,{'sign_out':sign_out})
                cr.commit()
                cr.close()
        except Exception,e:
            _logger.info("=======%s",e)
        return res



class res_users_log(osv.osv):
    _name='res.users.log'
    _order = 'sign_in desc'
    _columns={
              'user_id': fields.many2one('res.users','User'),
              'sign_in':fields.datetime('Login Time'),
              'sign_out':fields.datetime('Logout Time'),
              'session_id':fields.char('Session ID'),
              }
