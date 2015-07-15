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
import openerp.addons.decimal_precision as dp

class WizSaleCreateFictious(models.TransientModel):
    _name = "wiz.sale.create.fictitious"

    date_planned = fields.Datetime(
        string='Scheduled Date', required=True, default=fields.Datetime.now())
    load_on_product = fields.Boolean("Load cost on product")
    project_id = fields.Many2one("project.project", string="Project")
    production_sale_margin_id = fields.Many2one('production.sale.margin','Mfg Sales Multiplier ')
    sale_order_id = fields.Many2one("sale.order", string= "Sales Order")
    product_id = fields.Many2one("product.product" , string="Product")
    product_qty = fields.Float('Product Quantity', digits_compute=dp.get_precision('Product Unit of Measure'))
    product_uom = fields.Many2one('product.uom', 'Product Unit of Measure',  readonly=False)
    product_uos_qty = fields.Float('Product UoS Quantity', readonly=False)
    product_uos = fields.Many2one('product.uom', 'Product UoS', readonly=False)
    bom_id = fields.Many2one('mrp.bom', 'Bill of Material', readonly=False,
            help="Bill of Materials allow you to define the list of required raw materials to make a finished product.")
    routing_id = fields.Many2one('mrp.routing', string='Routing', on_delete='set null', readonly=False,
            help="The list of operations (list of work centers) to produce the finished product. The routing is mainly used to compute work center costs during operations and to plan future loads on work centers based on production plannification.")


    @api.multi
    def do_create_fictitious_of_sale(self):
        production_obj = self.env['mrp.production']
        product_obj = self.env['product.product']
        project_obj = self.env['project.project']
        sale_line_obj = self.env['sale.order.line']
        
        self.ensure_one()
        active_id = self.env.context['active_id']
        active_model = self.env.context['active_model']
        production_list = []
        
        if active_model == 'sale.order':
            
            sale_order = self.env['sale.order'].browse(active_id)
            sale_line = sale_line_obj.create({'order_id':active_id,
                                              'product_id':self.product_id.id,
                                              'name':'mfg quote--' + self.product_id.name,
                                              'production_sale_margin_id':self.production_sale_margin_id.id})
            product =  sale_line.product_id

            vals = {'product_id': product.id,
                    'product_qty': 1,
                    'date_planned': self.date_planned,
                    'user_id': self._uid,
                    'active': True,
                    'is_sale_quote':True,
                    'product_qty': self.product_qty,
                    'product_uom' :self.product_uom.id,
                    'bom_id': self.bom_id.id,
                    'routing_id' : self.routing_id.id,
                    'sale_order_line_id': sale_line.id,
                    'sale_order_id': active_id,
                    'origin': sale_order.name
                    
                    }
            new_production = production_obj.create(vals)
            new_production.action_compute()
            new_production.calculate_production_estimated_cost()
            production_list.append(new_production.id)
            if new_production.project_id and self.project_id.id:
                new_production.project_id.write({"parent_id":self.project_id.analytic_account_id.id})
            sale_line.write({'production_id':new_production.id})
            
        if self.load_on_product:
            for production_id in production_list:
                try:
                    production = production_obj.browse(production_id)
                    production.calculate_production_estimated_cost()
                    production.load_product_std_price()
                except:
                    continue
        return{}
        '''return {'view_type': 'form',
                'view_mode': 'form, tree',
                'res_model': 'mrp.production',
                'type': 'ir.actions.act_window',
                'target':'new',
                'domain': "[('id','in'," + str(production_list) + "), "
                "('active','=',False)]",
                'res_id':  production_list[0],
                
                }'''
        
    def product_id_change(self, cr, uid, ids, product_id, product_qty=0, context=None):
        """ Finds UoM of changed product.
        @param product_id: Id of changed product.
        @return: Dictionary of values.
        """
        result = {}
        if not product_id:
            return {'value': {
                'product_uom': False,
                'bom_id': False,
                'routing_id': False,
                'product_uos_qty': 0,
                'product_uos': False
            }}
        bom_obj = self.pool.get('mrp.bom')
        product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        bom_id = bom_obj._bom_find(cr, uid, product_id=product.id, properties=[], context=context)
        routing_id = False
        if bom_id:
            bom_point = bom_obj.browse(cr, uid, bom_id, context=context)
            routing_id = bom_point.routing_id.id or False
        product_uom_id = product.uom_id and product.uom_id.id or False
        result['value'] = {'product_uos_qty': 0, 'product_uos': False, 'product_uom': product_uom_id, 'bom_id': bom_id, 'routing_id': routing_id}
        if product.uos_id.id:
            result['value']['product_uos_qty'] = product_qty * product.uos_coeff
            result['value']['product_uos'] = product.uos_id.id
            self.write(cr, uid, ids,result['value'],context=context)
        return result
    

    
    def default_get(self, cr, uid, fields, context=None):
        
        res = super(WizSaleCreateFictious, self).default_get(cr, uid, fields, context)    
        if context is None:
            context = {}  
              
        sale_order_obj = self.pool.get('sale.order').browse(cr, uid, context['active_id'], context=context)
              
        project =  sale_order_obj.main_project_id
        res['project_id'] = project.id
        res['sale_order_id'] = context['active_id']
        res['product_qty'] = 1.0
        return res
    
    

    