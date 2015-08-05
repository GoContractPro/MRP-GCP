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

from openerp import models, fields, api, exceptions, _



class procurement_order(models.Model):
    _inherit = 'procurement.order'
    
    def make_mo(self, cr, uid, procurement, context=None):
        """ Make Manufacturing(production) order from procurement
        @return: New created Production Orders procurement wise
        """
        if procurement.sale_line_id and procurement.sale_line_id.production_id:
            return {procurement.id : False}
        return super(procurement_order, self).make_mo(cr, uid, procurement, context=context)
    
    def _run(self, cr, uid, procurement, context=None):
        result = super(procurement_order, self)._run(cr, uid, procurement, context=context)
        if procurement.sale_line_id and procurement.sale_line_id.production_id:
            res = {}
            production_obj = self.pool.get('mrp.production')
            defaults = self._prepare_mo_vals(cr, uid, procurement, context=context)
            defaults['sale_order_line_id'] = procurement.sale_line_id.id         
            defaults['sale_order_id'] = procurement.sale_line_id.order_id.id
            defaults['analytic_account_id'] = procurement.sale_line_id.order_id.project_id.id
            defaults['project'] = procurement.sale_line_id.order_id.main_project_id.id       
            defaults['is_sale_quote'] = False

            new_production = procurement.sale_line_id.production_id.copy(defaults)
            
            procurement.sale_line_id.write({'production_actual_id':new_production.id})
#            self.write(cr, uid, [procurement.id], {'production_id': new_production.id})
            self.production_order_create_note(cr, uid, procurement, context=context)
            production_obj.signal_workflow(cr, uid, [new_production.id], 'button_confirm')

            res[procurement.id] = new_production
            return res
        else:
            return result


            
        
    