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


from openerp import models, fields, api


class Wiz_Sale_Create_Fictitious(models.TransientModel):
    _name = "wiz.sale.create.fictitious"

    date_planned = fields.Datetime(
        string='Scheduled Date', required=True, default=fields.Datetime.now())
    load_on_product = fields.Boolean("Load cost on product")
    project_id = fields.Many2one("project.project", string="Project")

    @api.multi
    def do_create_fictitious_of_sale(self):
        production_obj = self.env['mrp.production']
        product_obj = self.env['product.product']
        sale_line_obj = self.env['sale.order.line']
        self.ensure_one()
        active_ids = self.env.context['active_ids']
        active_model = self.env.context['active_model']
        production_list = []
        if active_model == 'sale.order.line':
            
            product =  sale_line_obj.browse(active_ids).product_id


            vals = {'product_id': product.id,
                    'product_qty': 1,
                    'date_planned': self.date_planned,
                    'user_id': self._uid,
                    'active': False,
                    'product_uom': product.uom_id.id,
                    'project_id': self.project_id.id
                    }
            new_production = production_obj.create(vals)
            new_production.action_compute()
            production_list.append(new_production.id)
            
        if self.load_on_product:
            for production_id in production_list:
                try:
                    production = production_obj.browse(production_id)
                    production.calculate_production_estimated_cost()
                    production.load_product_std_price()
                except:
                    continue
        return {'view_type': 'form',
                'view_mode': 'form, tree',
                'res_model': 'mrp.production',
                'type': 'ir.actions.act_window',
                'target':'new',
                'domain': "[('id','in'," + str(production_list) + "), "
                "('active','=',False)]",
                'res_id':  production_list[0],
                
                }

    def default_get(self, cr, uid, fields, context=None):
        
        ret = super(Wiz_Sale_Create_Fictitious,self).default_get(cr, uid, fields, context=context)
            
        if context is None:
            context = {}  
              
        sale_line_obj = self.pool.get('sale.order.line').browse(cr, uid, context['active_id'], context=context)
        sale_order_object =sale_line_obj.order_id      
        project =  sale_order_object.main_project_id
        ret['project_id'] = project.id
        return ret
