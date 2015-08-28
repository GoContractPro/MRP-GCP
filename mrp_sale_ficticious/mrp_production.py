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
    def create_production_estimated_cost(self):
        production = self
        if production.sale_order_line_id:
            self.create_sale_analytic_production_estimated_cost(sale_order_line = production.sale_order_line_id, product_uom_qty = production.sale_order_line_id.product_uom_qty )
        else:
            super(MrpProduction, self).create_production_estimated_cost()
            
    @api.multi
    def get_product_cost(self, product):
        
        return product.manual_standard_cost or product.cost_price or product.standard_price 

    @api.multi
    def calculate_production_estimated_cost(self):
        analytic_line_obj = self.env['account.analytic.line']
        for record in self:
            cond = [('mrp_production_id', '=', record.id)]
            analytic_line_obj.search(cond).unlink()
            journal = record.env.ref('mrp_production_project_estimated_cost.'
                                     'analytic_journal_materials', False)
            for line in record.product_lines:
                if not line.product_id:
                    raise exceptions.Warning(
                        _("One consume line has no product assigned."))
                name = _('%s-%s' % (record.name, line.work_order.name or ''))
                product = line.product_id
                qty = line.product_qty
                amount = -qty * self.get_product_cost(product) 
                vals = record._prepare_cost_analytic_line(
                    journal, name, record, product, workorder=line.work_order,
                    qty=qty, estim_std=-(qty * product.manual_standard_cost),
                    estim_avg=-amount)
                analytic_line_obj.create(vals)
            journal = record.env.ref('mrp_production_project_estimated_cost.'
                                     'analytic_journal_machines', False)
            for line in record.workcenter_lines:
                op_wc_lines = line.routing_wc_line.op_wc_lines
                wc = op_wc_lines.filtered(lambda r: r.workcenter ==
                                          line.workcenter_id) or \
                    line.workcenter_id
                if (wc.time_start and line.workcenter_id.pre_op_product):
                    name = (_('%s-%s Pre-operation') %
                            (record.name, line.workcenter_id.name))
                    product = line.workcenter_id.pre_op_product
                    amount = self.get_product_cost(product) * wc.time_start
                    qty = wc.time_start
                    vals = record._prepare_cost_analytic_line(
                        journal, name, record, product, workorder=line,
                        qty=qty, amount=-amount,
                        estim_std=-(qty * product.manual_standard_cost),
                        estim_avg=-(amount))
                    analytic_line_obj.create(vals)
                if (wc.time_stop and line.workcenter_id.post_op_product):
                    name = (_('%s-%s Post-operation') %
                            (record.name, line.workcenter_id.name))
                    product = line.workcenter_id.post_op_product
                    amount = self.get_product_cost(product) * wc.time_stop
                    qty = wc.time_stop
                    vals = record._prepare_cost_analytic_line(
                        journal, name, record, product, workorder=line,
                        qty=qty, amount=-amount,
                        estim_std=-(qty * product.manual_standard_cost),
                        estim_avg=-(amount))
                    analytic_line_obj.create(vals)
                if line.cycle and line.workcenter_id.costs_cycle:
                    if not line.workcenter_id.product_id:
                        raise exceptions.Warning(
                            _("There is at least this workcenter without "
                              "product: %s") % line.workcenter_id.name)
                    name = (_('%s-%s-C-%s') %
                            (record.name, line.routing_wc_line.operation.code,
                             line.workcenter_id.name))
                    product = line.workcenter_id.product_id
                    estim_cost = -(line.workcenter_id.costs_cycle * line.cycle)
                    vals = record._prepare_cost_analytic_line(
                        journal, name, record, product, workorder=line,
                        qty=line.cycle, estim_std=estim_cost,
                        estim_avg=estim_cost)
                    analytic_line_obj.create(vals)
                if line.hour and line.workcenter_id.costs_hour:
                    if not line.workcenter_id.product_id:
                        raise exceptions.Warning(
                            _("There is at least this workcenter without "
                              "product: %s") % line.workcenter_id.name)
                    name = (_('%s-%s-H-%s') %
                            (record.name, line.routing_wc_line.operation.code,
                             line.workcenter_id.name))
                    hour = line.hour
                    if wc.time_stop and not line.workcenter_id.post_op_product:
                        hour += wc.time_stop
                    if wc.time_start and not line.workcenter_id.pre_op_product:
                        hour += wc.time_start
                    estim_cost = -(hour * line.workcenter_id.costs_hour)
                    vals = record._prepare_cost_analytic_line(
                        journal, name, record, line.workcenter_id.product_id,
                        workorder=line, qty=hour,
                        estim_std=estim_cost, estim_avg=estim_cost)
                    analytic_line_obj.create(vals)
                if wc.op_number > 0 and line.hour:
                    if not line.workcenter_id.product_id:
                        raise exceptions.Warning(
                            _("There is at least this workcenter without "
                              "product: %s") % line.workcenter_id.name)
                    journal = record.env.ref(
                        'mrp_production_project_estimated_cost.analytic_'
                        'journal_operators', False)
                    name = (_('%s-%s-%s') %
                            (record.name, line.routing_wc_line.operation.code,
                             line.workcenter_id.product_id.name))
                    estim_cost = -(wc.op_number * wc.op_avg_cost * line.hour)
                    qty = line.hour * wc.op_number
                    vals = record._prepare_cost_analytic_line(
                        journal, name, record, line.workcenter_id.product_id,
                        workorder=line, qty=qty, estim_std=estim_cost,
                        estim_avg=estim_cost)
                    analytic_line_obj.create(vals)

    @api.multi                
    def _prepare_analytic_line(self, journal, name, production = None , product = None,
                                    general_account=None, workorder=None,
                                    qty=1, amount=0, estim_std=0, estim_avg=0 ):
        
        
        res = super(MrpProduction, self)._prepare_analytic_line(journal, name, production = production , product = product,
                                    general_account=None, workorder=None,
                                    qty= qty, amount=amount, estim_std=estim_std, estim_avg=estim_avg)
        
        if production.sale_order_line:
            
            res['sale_order_line_id'] = production.sale_order_line_id.id or False,

        return res
    
    @api.multi                
    def _prepare_sale_cost_analytic_line(self, journal, name, sale_order_line, product,
                                    general_account=None, workorder=None,
                                    qty=1, amount=0, estim_std=0, estim_avg=0):
        
        analytic_line_obj = self.env['account.analytic.line']
        property_obj = self.env['ir.property']
        if not general_account:
            general_account = (product.property_account_income or
                               product.categ_id.property_account_income_categ
                               or property_obj.get(
                                   'property_account_expense_categ',
                                   'product.category'))
        if not sale_order_line.order_id.project_id:
            raise exceptions.Warning(
                _('You must define one Project for this Sale Order Quote: %s') %
                (self.sale_order_id.name))
        vals = {
            'name': name,
            'sale_order_line_id': sale_order_line and sale_order_line.id or False,
            'workorder': workorder and workorder.id or False,
            'account_id': sale_order_line.order_id.project_id.id,#Analytic Account ID
            'journal_id': journal.id,
            'user_id': self.env.uid,
            'date': analytic_line_obj._get_default_date(),
            'product_id': product and product.id or False,
            'unit_amount': qty,
            'amount': amount,
            'product_uom_id': product and product.uom_id.id or False,
            'general_account_id': general_account.id,
            'estim_std_cost': estim_std,
            'estim_avg_cost': estim_avg,
        }
        return vals

    @api.multi
    def create_sale_analytic_production_estimated_cost(self, sale_order_line=None, product_uom_qty = False):
        
        analytic_line_obj = self.env['account.analytic.line']
        cond = [('sale_order_line_id', '=', sale_order_line.id)]
        analytic_line_obj.search(cond).unlink()
        journal = self.env.ref('mrp_production_project_estimated_cost.'
                                 'analytic_journal_materials', False)

        production = self
        if not sale_order_line:
            raise exceptions.Warning(
                    _("Sale Order Line Required."))
        
        if not product_uom_qty:
            raise exceptions.Warning(
                    _("Sale Order Line Quantity Required."))
        
        
        for line in production.product_lines:
            if not line.product_id:
                raise exceptions.Warning(
                    _("One consume line has no product assigned."))
            name = _('%s-%s' % (production.name, line.work_order.name or ''))
            product = line.product_id
            qty = line.product_qty * product_uom_qty
            amount = -qty * self.get_product_cost(product)
            vals = production._prepare_sale_cost_analytic_line(
                journal, name, sale_order_line = sale_order_line, product = product, workorder=line.work_order,
                qty=qty, estim_std=-(qty * product.manual_standard_cost),
                estim_avg= amount )
            analytic_line_obj.create(vals)
        journal = production.env.ref('mrp_production_project_estimated_cost.'
                                 'analytic_journal_machines', False)
        for line in production.workcenter_lines:
            op_wc_lines = line.routing_wc_line.op_wc_lines
            wc = op_wc_lines.filtered(lambda r: r.workcenter ==
                                      line.workcenter_id) or \
                line.workcenter_id
            if (wc.time_start and line.workcenter_id.pre_op_product):
                name = (_('%s-%s Pre-operation') %
                        (production.name, line.workcenter_id.name))
                product = line.workcenter_id.pre_op_product
                amount = self.get_product_cost(product) * wc.time_start
                qty = wc.time_start
                vals = production._prepare_sale_cost_analytic_line(
                    journal, name, sale_order_line = sale_order_line, product = product, workorder=line,
                    qty=qty, amount=-amount,
                    estim_std=-(qty * product.manual_standard_cost),
                    estim_avg=-(amount))
                analytic_line_obj.create(vals)
            if (wc.time_stop and line.workcenter_id.post_op_product):
                name = (_('%s-%s Post-operation') %
                        (production.name, line.workcenter_id.name))
                product = line.workcenter_id.post_op_product
                amount = self.get_product_cost(product) * wc.time_stop
                qty = wc.time_stop
                vals = production._prepare_sale_cost_analytic_line(
                    journal, name, sale_order_line = sale_order_line, product = product, workorder=line,
                    qty=qty, amount=-amount,
                    estim_std=-(qty * product.manual_standard_cost),
                    estim_avg=-(amount))
                analytic_line_obj.create(vals)
            if line.cycle and line.workcenter_id.costs_cycle:
                if not line.workcenter_id.product_id:
                    raise exceptions.Warning(
                        _("There is at least this workcenter without "
                          "product: %s") % line.workcenter_id.name)
                name = (_('%s-%s-C-%s') %
                        (production.name, line.routing_wc_line.operation.code,
                         line.workcenter_id.name))
                product = line.workcenter_id.product_id
                estim_cost = -(line.workcenter_id.costs_cycle * line.cycle) *  product_uom_qty
                vals = production._prepare_sale_cost_analytic_line(
                    journal, name, sale_order_line = sale_order_line, product = product, workorder=line,
                    qty=line.cycle, estim_std=estim_cost,
                    estim_avg=estim_cost)
                analytic_line_obj.create(vals)
            if line.hour and line.workcenter_id.costs_hour:
                if not line.workcenter_id.product_id:
                    raise exceptions.Warning(
                        _("There is at least this workcenter without "
                          "product: %s") % line.workcenter_id.name)
                name = (_('%s-%s-H-%s') %
                        (production.name, line.routing_wc_line.operation.code,
                         line.workcenter_id.name))
                hour = line.hour *  product_uom_qty
                if wc.time_stop and not line.workcenter_id.post_op_product:
                    hour += wc.time_stop
                if wc.time_start and not line.workcenter_id.pre_op_product:
                    hour += wc.time_start
                estim_cost = -(hour * line.workcenter_id.costs_hour)
                vals = production._prepare_sale_cost_analytic_line(
                    journal, name, sale_order_line = sale_order_line, product = line.workcenter_id.product_id,
                    workorder=line, qty=hour,
                    estim_std=estim_cost, estim_avg=estim_cost)
                analytic_line_obj.create(vals)
            if wc.op_number > 0 and line.hour:
                if not line.workcenter_id.product_id:
                    raise exceptions.Warning(
                        _("There is at least this workcenter without "
                          "product: %s") % line.workcenter_id.name)
                journal = production.env.ref(
                    'mrp_production_project_estimated_cost.analytic_'
                    'journal_operators', False)
                name = (_('%s-%s-%s') %
                        (production.name, line.routing_wc_line.operation.code,
                         line.workcenter_id.product_id.name))
                estim_cost = -(wc.op_number * wc.op_avg_cost * line.hour) * product_uom_qty
                qty = line.hour * wc.op_number * product_uom_qty
                
                vals = production._prepare_sale_cost_analytic_line(
                    journal, name, sale_order_line = sale_order_line, product = line.workcenter_id.product_id,
                    workorder=line, qty=qty, estim_std=estim_cost,
                    estim_avg=estim_cost)
                analytic_line_obj.create(vals)
        
        return True

    @api.model
    def create(self, values):
        sequence_obj = self.env['ir.sequence']
        if values.get('is_sale_quote', False):
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
        
        cond = [('production_id','=',self.id)]
        so_lines_to_update = self.env['sale.order.line'].search(cond)
        
        for line in so_lines_to_update:
            
            for line.state in ['draft']:
                self.update_mfg_sale_line_price(line)
            
        return super(MrpProduction, self).write(vals,update=update,mini=mini)
    
    @api.multi
    def update_mfg_sale_line_price(self, sale_line):
        
        if sale_line.production_id:
            prices = sale_line.get_production_sale_line_price(sale_line.product_uom_qty, sale_line.production_sale_margin_id.id)
            sale_line.write(prices)
        return True

    @api.multi
    def copy(self,default=None):
        
#        default = {} if default is None else default.copy()
        
#        default['origin'] = (self.origin or '') + "[Copy-" + (self.name or '') + "]"         
        return super(MrpProduction, self).copy( default)
            


