# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 novapointgroup inc.
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

from openerp import models, fields, api, _

class procurement_rule(models.Model):
    _inherit = 'procurement.rule'

    @api.multi
    def _get_action(self):
        return [('sale_manufacture', _('Sales MFG Quoted'))] + super(procurement_rule, self)._get_action()

class procurement_order(models.Model):
    _inherit = 'procurement.order'
    
    
    def _run(self,cr,uid,procurement, context=None):
        
        if procurement.sale_line_id and procurement.sale_line_id.production_id:
            new_production = procurement.sale_line_id.production_id.copy()
            origin = procurement.sale_line_id.production_id.origin or ''
            quantity = procurement.sale_line_id.product_uom_qty or 0.0
            sequence_obj = procurement.env['ir.sequence']
            vals = {'name':sequence_obj.get('mrp.production'),
                    'origin':(origin) + "/" + (procurement.sale_line_id.production_id.name or ''),
                    'product_qty':quantity,
                    }
            new_production.write(vals)
            res = {}
            res[procurement.id] = new_production
            return res
        else:
            return super(procurement_order, self)._run(cr, uid, procurement, context=context)


            
        
    