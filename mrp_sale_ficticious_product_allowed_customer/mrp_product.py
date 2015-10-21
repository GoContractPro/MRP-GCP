# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 NovaPoint Group INC (<http://www.novapointgroup.com>)
#    Copyright (C) 2004-2010 OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp.osv import fields, osv

class product_template(osv.osv):
    _inherit = "product.template"
    _columns = {
        'customer_id':fields.many2one("res.partner","Customer"),
    }

class WizSaleCreateFictious(osv.osv):
    _inherit = "wiz.sale.create.fictitious"
    
    _columns = {
        'customer_id':fields.many2one("res.partner","Customer"),
    }
    
    def default_get(self, cr, uid, fields, context=None):
        res = super(WizSaleCreateFictious, self).default_get(cr, uid, fields, context)
        so_id = context.get('active_id')
        if so_id:
            res ['customer_id'] = self.pool.get('sale.order').browse(cr,uid,so_id,context=context).partner_id.id
        return res
    
