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

from openerp import models, fields, api, exceptions , _

WARNING_TYPES = [('warning','Warning'),('info','Information'),('error','Error')]

class mrp_sale_warning(models.TransientModel):
    _name = 'mrp.sale.warning'
    _description = 'warning'
    
    type = fields.Selection(WARNING_TYPES, string='Type', readonly=True)
    title = fields.Char(string="Title", size=100, readonly=True)
    msg = fields.Text(string="Message", readonly=True)

    _req_name = 'title'
    
    lines_to_delete = []
    
    @api.multi
    def _get_view_id(self):
        """Get the view id
        @return: view id, or False if no view found
        """
        res = self.env['ir.model.data'].env.ref('mrp_sale_ficticious.warning_sale_mrp_form',False)
        return res.id or False
    
    @api.multi
    def message(self):
        
        message_type = [t[1]for t in WARNING_TYPES if self.type == t[0]][0]
        print '%s: %s' % (_(message_type), _(self.title))
        res = {
            'name': '%s: %s' % (_(message_type), _(self.title)),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self._get_view_id(),
            'res_model': 'mrp.sale.warning',
            'domain': [],
            'context': self.env.context,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': self.id
        }
        return res
    
    
    def delete_with_warning(self, cr, uid, title, message, lines_delete, context=None):
        id = self.create(cr, uid, {'title': title, 'msg': message, 'type': 'warning', })
        self.lines_to_delete = lines_delete
        res = self.message(cr, uid, id, context)
        return res
    
    def info(self, cr, uid, title, message, context=None):
        id = self.create(cr, uid, {'title': title, 'msg': message, 'type': 'info'})
        res = self.message(cr, uid, id, context)
        return res
    
    def error(self, cr, uid, title, message, context=None):
        id = self.create(cr, uid, {'title': title, 'msg': message, 'type': 'error'})
        res = self.message(cr, uid, id, context)
        return res
    
    @api.multi
    def action_continue_sale_confirm(self):
        
        active_id = self.env.context['active_id']
        active_model = self.env.context['active_model']
        if active_model == 'sale.order':
            sale_obj = self.env['sale.order'].browse(active_id)
            sale_line_obj = self.env['sale.order.line']
            analytic_line_obj = self.env['account.analytic.line'] 
            lines = sale_line_obj.browse(self.lines_to_delete)
            #delete those analytic lines which sale order 
            #line production approved field is unchecked 
            lines_delete_lst = []
            [lines_delete_lst.append(rec.id) for rec in sale_obj.order_line if rec.production_id and not rec.is_approved]
            if lines_delete_lst:
                analytic_line_id = analytic_line_obj.search([('sale_order_line_id','in',lines_delete_lst)])
                if analytic_line_id :
                    for rec in analytic_line_id:rec.unlink()
                    
            if lines:
                lines.unlink()
            return sale_obj.action_button_confirm()
            
        else:
            return False
        
        
        
    def action_cancel_sale_confirm(self, cr, uid, title, message, context=None):
        
        return False