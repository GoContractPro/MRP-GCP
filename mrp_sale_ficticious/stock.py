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


class stock_move(models.Model):
    _inherit = "stock.move"    
    
    
    def _prepare_procurement_from_move(self, cr, uid, move, context=None):
        res = super(stock_move, self)._prepare_procurement_from_move(cr, uid, move, context=context)
        if res and move.procurement_id and move.procurement_id.sale_line_id and move.procurement_id.sale_line_id.production_id:
            res['sale_line_id'] = move.procurement_id.sale_line_id.id
        return res