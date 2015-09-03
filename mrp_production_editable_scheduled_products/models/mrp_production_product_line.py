# -*- encoding: utf-8 -*-
##############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################

from openerp import models, fields, api, _

class MrpProductionProductLine(models.Model):
    _inherit = 'mrp.production.product.line'

    @api.multi
    @api.onchange('product_id')
    def onchange_product_id(self, product_id):
        
        res={}
        res['value']={}
        
        if product_id:
        
            product = self.env['product.product'].browse(product_id)           
            res['value']['name'] = product.name
                  
        return res
    

    @api.model
    def default_get(self, var_fields):
            
 
        res = super(MrpProductionProductLine, self).default_get(
            var_fields) 
 
        production_id = self.env.context.get('active_id',False)
        res['production_id'] = production_id
        
        return res 