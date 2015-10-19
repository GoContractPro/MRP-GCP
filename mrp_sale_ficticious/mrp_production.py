# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
import math


class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    
    sale_order_line_id = fields.Many2one("sale.order.line", string= "Sales Line", ondelete='cascade')
    sale_order_id = fields.Many2one("sale.order", string= "Sale Order ")
    sale_project_id =  fields.Many2one("project.project", string="Sales Project")
    is_sale_quote = fields.Boolean("Confirmed Quote", default=lambda self: self.env.context.get('default_is_sale_quote',False))
    product_lines = fields.One2many('mrp.production.product.line', 'production_id', 'Scheduled goods',
            readonly=True,copy=True )
    workcenter_lines = fields.One2many('mrp.production.workcenter.line', 'production_id', 'Work Centers Utilisation',
            readonly=True, states={'draft': [('readonly', False)]},copy=True)
   

    @api.multi
    def action_show_estimated_costs(self):
        self.ensure_one()
        analytic_line_obj = self.env['account.analytic.line']
        id2 = self.env.ref(
            'mrp_sale_ficticious.estimated_cost_list_view_inherit1')
        search_view = self.env.ref('mrp_project_link.account_analytic_line'
                                   '_mrp_search_view')
        if self.sale_order_line_id:
            analytic_line_list = analytic_line_obj.search(
            [('sale_order_line_id', '=', self.sale_order_line_id.id),
             ('task_id', '=', False)])        
        else:
            analytic_line_list = analytic_line_obj.search(
            [('mrp_production_id', '=', self.id),
             ('task_id', '=', False)])
        self = self.with_context(
                                 search_default_group_workorder=1,
                                 search_default_group_journal=1)
        return {
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.analytic.line',
            'views': [(id2.id, 'tree')],
            'search_view_id': search_view.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'window',
            'domain': "[('id','in',[" +
            ','.join(map(str, analytic_line_list.ids)) + "])]",
            'context': self.env.context
            }
        

            
    @api.multi
    def get_product_cost(self, product):
        
        return product.manual_standard_cost or product.cost_price or product.standard_price 
    
    @api.multi
    def create_journal_estimate_products(self, product_line= None, sale_order_line=None,  factor = 0):
        
        journal = self.env.ref('mrp_production_project_estimated_cost.'
                                     'analytic_journal_materials', False)

        if not product_line.product_id:
            raise exceptions.Warning(
                    _("One consume line has no product assigned."))
            
        name = _('%s-%s' % (self.name, product_line.work_order.name or ''))
        
        qty = product_line.product_qty
        qty = qty*factor
        
        amount = -qty * self.get_product_cost(product_line.product_id)
        
        
         
        vals = self._prepare_cost_analytic_line(
                journal, name,
                self, 
                product=product_line.product_id, 
                workorder=product_line.work_order,
                qty=qty, 
                estim_avg=amount,
                sale_order_line = sale_order_line) 
        
        self.env['account.analytic.line'].create(vals)
    
        return
            
    @api.multi
    def create_journal_estimate_pre_operations(self, workorder=None, wc=None, sale_order_line=None):          
        
        if (wc.time_start and workorder.workcenter_id.pre_op_product):
            
            journal = self.env.ref('mrp_production_project_estimated_cost.'
                                     'analytic_journal_machines', False)
            name = (_('%s-%s Pre-operation') %
                    (self.name, workorder.workcenter_id.name))
            product = workorder.workcenter_id.pre_op_product
            
            qty = workorder.time_start

            amount = -(self.get_product_cost(product) * qty)

            vals = self._prepare_cost_analytic_line(
                journal, name, self, product, workorder=workorder,
                qty=qty, amount=amount,
                estim_std=qty * product.manual_standard_cost,
                estim_avg=amount,
                sale_order_line = sale_order_line)
            
            self.env['account.analytic.line'].create(vals)
            
            
    @api.multi
    def create_journal_estimate_post_operations(self, workorder=None, wc=None, sale_order_line=None):
 
        
        if (wc.time_stop and workorder.workcenter_id.post_op_product):
            
            journal = self.env.ref('mrp_production_project_estimated_cost.'
                                     'analytic_journal_machines', False)
            name = (_('%s-%s Post-operation') %
                    (self.name, workorder.workcenter_id.name))
            product = workorder.workcenter_id.post_op_product
            
            
            if product:
                qty = wc.time_stop
                
                amount = -self.get_product_cost(product) * qty
                               
                vals = self._prepare_cost_analytic_line(
                    journal, name, self, product, workorder=workorder,
                    qty=qty, amount=amount,
                    estim_std = (qty * product.manual_standard_cost),
                    estim_avg = (amount),
                    sale_order_line = sale_order_line)
                self.env['account.analytic.line'].create(vals)
                
    @api.multi
    def create_journal_estimate_wc_cycle(self, workorder =  None, sale_order_line = None,  cycle=0):
         
        if workorder.cycle and workorder.workcenter_id.costs_cycle:
            
            journal = self.env.ref('mrp_production_project_estimated_cost.'
                         'analytic_journal_machines', False)

            if not workorder.workcenter_id.product_id:
                raise exceptions.Warning(
                    _("There is at least this workcenter without "
                      "product: %s") % workorder.workcenter_id.name)
            name = (_('%s-%s-C-%s') %
                    (self.name, workorder.routing_wc_line.operation.code,
                     workorder.workcenter_id.name))
            product = workorder.workcenter_id.product_id
            
            qty = workorder.cycle
            
            qty = qty*cycle
            
            estim_cost = -(workorder.workcenter_id.costs_cycle * qty)         
            
            vals = self._prepare_cost_analytic_line(
                journal, name, self, product, workorder=workorder,
                qty=qty, estim_std=estim_cost,
                estim_avg=estim_cost,
                sale_order_line = sale_order_line)
            
            self.env['account.analytic.line'].create(vals) 
     
           
    @api.multi
    def create_journal_estimate_wc_hourly(self, workorder=None, wc=None, sale_order_line=None,  cycle=0):
            
        journal = self.env.ref('mrp_production_project_estimated_cost.'
                                     'analytic_journal_machines', False)
    
        if workorder.hour and workorder.workcenter_id.costs_hour:
            if not workorder.workcenter_id.product_id:
                raise exceptions.Warning(
                    _("There is at least this workcenter without "
                      "product: %s") % workorder.workcenter_id.name)
            name = (_('%s-%s-H-%s') %
                    (self.name, workorder.routing_wc_line.operation.code,
                     workorder.workcenter_id.name))
            
            hour = workorder.hour
           
            hour = hour*cycle
            
            if workorder.time_stop and not workorder.workcenter_id.post_op_product:
                hour += workorder.time_stop
            if workorder.time_start and not workorder.workcenter_id.pre_op_product:
                hour += workorder.time_start
            estim_cost = -(hour * workorder.workcenter_id.costs_hour)
            vals = self._prepare_cost_analytic_line(
                journal, name, self, workorder.workcenter_id.product_id,
                workorder=workorder, qty=hour,
                estim_std=estim_cost, estim_avg=estim_cost,
                sale_order_line = sale_order_line)
            self.env['account.analytic.line'].create(vals)

    @api.multi
    def create_journal_estimate_operators(self, workorder= None, wc=None, sale_order_line=None,  cycle=None):
                         
        if wc.op_number > 0 and workorder.hour:
            
            if not workorder.workcenter_id.product_id:
                raise exceptions.Warning(
                    _("There is at least this workcenter without "
                      "product: %s") % workorder.workcenter_id.name)
            journal = self.env.ref(
                'mrp_production_project_estimated_cost.analytic_'
                'journal_operators', False)
            name = (_('%s-%s-%s') %
                    (self.name, workorder.routing_wc_line.operation.code,
                     workorder.workcenter_id.product_id.name))
            
            
            hour = workorder.hour
            hour = hour*cycle
            
            estim_cost = -(wc.op_number * wc.op_avg_cost * hour)
            qty = workorder.hour * wc.op_number
            vals = self._prepare_cost_analytic_line(
                journal, name, self, workorder.workcenter_id.product_id,
                workorder=workorder, qty=qty, estim_std=estim_cost,
                estim_avg=estim_cost,
                sale_order_line = sale_order_line)
            
            self.env['account.analytic.line'].create(vals)  
            
    @api.multi
    def calculate_production_estimated_cost(self):
        
        
        self.update_sale_lines_producion_cost_estimates()
        return self._calculate_production_estimated_cost(None, None)
           
    @api.multi
    def _calculate_production_estimated_cost(self, sale_order_line=None, sale_qty=None):
            
        for record in self:
            
            analytic_line_obj = self.env['account.analytic.line']
            if sale_order_line:
                cond = [('sale_order_line_id', '=', sale_order_line.id)]
                recs = analytic_line_obj.search(cond)
                recs.unlink()
                factor = sale_qty
            else:
                cond = [('mrp_production_id', '=', record.id)]
                recs = analytic_line_obj.search(cond)
                recs.unlink()
                factor = self.product_qty
                
            for product_line in record.product_lines:
                
                self.create_journal_estimate_products(product_line, sale_order_line, factor)            

            for workorder in record.workcenter_lines:
# TODO: code here would optionally get work center Cycle Capacity fRom Possible Workcenters
#        need to define a rule on selecting the possible WC based on Cost or Capacity

                cycle_capacity = workorder.routing_wc_line.cycle_nbr
                
                possible_wc = workorder.routing_wc_line.op_wc_lines
                wc_from_possible_wc = possible_wc.filtered(lambda r: r.workcenter == workorder.workcenter_id) 
                if wc_from_possible_wc:
                    wc = wc_from_possible_wc.workcenter
                    cycle_capacity = wc_from_possible_wc.capacity_per_cycle  or 0
               
                else:
                    wc = workorder.routing_wc_line.workcenter_id
                    cycle_capacity = workorder.routing_wc_line.cycle_nbr or 0
                    
                if cycle_capacity:
                    cycle = cycle_capacity and int(math.ceil(factor / cycle_capacity)) or 0
                else:
                    cycle = 0
                
                self.create_journal_estimate_wc_cycle(workorder, sale_order_line, cycle)
                self.create_journal_estimate_wc_hourly(workorder, wc, sale_order_line, cycle)
                self.create_journal_estimate_pre_operations(workorder, wc, sale_order_line)
                self.create_journal_estimate_post_operations(workorder, wc, sale_order_line)
                self.create_journal_estimate_operators(workorder, wc, sale_order_line, cycle)

        return
    

    @api.multi                
    def _prepare_cost_analytic_line(self, journal, name, production = None , product = None,
                                    general_account=None, workorder=None,
                                    qty=1, amount=0, estim_std=0, estim_avg=0, sale_order_line=None ):
        
        
        res = super(MrpProduction, self)._prepare_cost_analytic_line(journal, name, production = production , product = product,
                                    general_account=general_account, workorder=workorder,
                                    qty= qty, amount=amount, estim_std=estim_std, estim_avg=estim_avg)
        
        if sale_order_line:
            if not sale_order_line.order_id.project_id:
                raise exceptions.Warning(
                    _('You must define one Project for this Sale Order Quote: %s') %
                    (self.sale_order_id.name))
            
            res['mrp_production_id']  = False
            res['sale_order_line_id'] = sale_order_line.id or False
            res['account_id'] = sale_order_line.order_id.main_project_id.analytic_account_id.id

        return res
        
    @api.multi
    def update_sale_lines_producion_cost_estimates(self):
        
        cond = [('production_id','=',self.id),('state','=','draft')]
        so_lines_to_update = self.env['sale.order.line'].search(cond)
        
        for line in so_lines_to_update:
            vals = line.get_sale_line_production_price_vals(product_uom_qty=line.product_uom_qty,production_sale_margin_id=line.production_sale_margin_id.id)
            line.write(vals)

    @api.model
    def create(self, values):
        sequence_obj = self.env['ir.sequence']
        if values.get('is_sale_quote', False) and not values.get('name', False):
            values['name'] = sequence_obj.get('sale.mrp.production')
        else:
            if values.get('active', True):
                values['active'] = True
                if values.get('name', '/') == '/':
                    values['name'] = sequence_obj.get('mrp.production')
            else:
                values['name'] = sequence_obj.get('fictitious.mrp.production')
        
            
        return super(MrpProduction, self).create(values)
    

    @api.one
    def write(self, vals, update=True, mini=True):

        self.update_sale_lines_producion_cost_estimates()
#        self.calculate_production_estimated_cost()

        return super(MrpProduction, self).write(vals,update=update,mini=mini)
    

    @api.multi
    def copy(self,default=None):
        
#        default = {} if default is None else default.copy()
        
#        default['origin'] = (self.origin or '') + "[Copy-" + (self.name or '') + "]"         
        return super(MrpProduction, self).copy( default)
            

         

 
