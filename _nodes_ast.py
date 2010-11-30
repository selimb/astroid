# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
# copyright 2003-2010 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
# copyright 2003-2010 Sylvain Thenault, all rights reserved.
# contact mailto:thenault@gmail.com
#
# This file is part of logilab-astng.
#
# logilab-astng is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 2.1 of the License, or (at your
# option) any later version.
#
# logilab-astng is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with logilab-astng. If not, see <http://www.gnu.org/licenses/>.
"""python 2.5 builtin _ast compatibility module

"""

__docformat__ = "restructuredtext en"


from _ast import (Expr as Discard, Str,
    # binary operators
    Add, Div, FloorDiv,  Mod, Mult, Pow, Sub, BitAnd, BitOr, BitXor,
    LShift, RShift,
    # logical operators
    And, Or,
    # unary operators
    UAdd, USub, Not, Invert,
    # comparison operators
    Eq, Gt, GtE, In, Is, IsNot, Lt, LtE, NotEq, NotIn,
    )

from logilab.astng import nodes as new
import sys

_BIN_OP_CLASSES = {Add: '+',
                   BitAnd: '&',
                   BitOr: '|',
                   BitXor: '^',
                   Div: '/',
                   FloorDiv: '//',
                   Mod: '%',
                   Mult: '*',
                   Pow: '**',
                   Sub: '-',
                   LShift: '<<',
                   RShift: '>>'}

_BOOL_OP_CLASSES = {And: 'and',
                    Or: 'or'}

_UNARY_OP_CLASSES = {UAdd: '+',
                     USub: '-',
                     Not: 'not',
                     Invert: '~'}

_CMP_OP_CLASSES = {Eq: '==',
                   Gt: '>',
                   GtE: '>=',
                   In: 'in',
                   Is: 'is',
                   IsNot: 'is not',
                   Lt: '<',
                   LtE: '<=',
                   NotEq: '!=',
                   NotIn: 'not in'}


CONST_NAME_TRANSFORMS = {'None':  None,
                         'True':  True,
                         'False': False}


def _init_set_doc(node, newnode):
    newnode.doc = None
    try:
        if isinstance(node.body[0], Discard) and isinstance(node.body[0].value, Str):
            newnode.tolineno = node.body[0].lineno
            newnode.doc = node.body[0].value.s
            node.body = node.body[1:]

    except IndexError:
        pass # ast built from scratch


from logilab.astng.rebuilder import RebuildVisitor
# _ast rebuilder ##############################################################

def _lineno_parent(oldnode, newnode, parent):
    newnode.parent = parent
    if hasattr(oldnode, 'lineno'):
        newnode.lineno = oldnode.lineno

class TreeRebuilder(RebuildVisitor):
    """Rebuilds the _ast tree to become an ASTNG tree"""

    def _set_infos(self, oldnode, newnode, parent):
        newnode.parent = parent
        if hasattr(oldnode, 'lineno'):
            newnode.lineno = oldnode.lineno
        last = newnode.last_child()
        newnode.set_line_info(last) # set_line_info accepts None

    def visit_arguments(self, node, parent):
        """visit a Arguments node by returning a fresh instance of it"""
        newnode = new.Arguments()
        _lineno_parent(node, newnode, parent)
        self.asscontext = "Ass"
        newnode.args = [self.visit(child, newnode) for child in node.args]
        self.asscontext = None
        newnode.defaults = [self.visit(child, newnode) for child in node.defaults]
        newnode.vararg = node.vararg
        newnode.kwarg = node.kwarg
        # save argument names in locals:
        if node.vararg:
            newnode.parent.set_local(newnode.vararg, newnode)
        if node.kwarg:
            newnode.parent.set_local(newnode.kwarg, newnode)
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_assattr(self, node, parent):
        """visit a AssAttr node by returning a fresh instance of it"""
        assc, self.asscontext = self.asscontext, None
        newnode = new.AssAttr()
        _lineno_parent(node, newnode, parent)
        newnode.expr = self.visit(node.expr, newnode)
        self.asscontext = assc
        self._delayed_assattr.append(newnode)
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_assert(self, node, parent):
        """visit a Assert node by returning a fresh instance of it"""
        newnode = new.Assert()
        _lineno_parent(node, newnode, parent)
        newnode.test = self.visit(node.test, newnode)
        newnode.fail = self.visit(node.msg, newnode)
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_assign(self, node, parent):
        """visit a Assign node by returning a fresh instance of it"""
        newnode = new.Assign()
        _lineno_parent(node, newnode, parent)
        self.asscontext = "Ass"
        newnode.targets = [self.visit(child, newnode) for child in node.targets]
        self.asscontext = None
        newnode.value = self.visit(node.value, newnode)
        self._set_assign_infos(newnode)
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_assname(self, node, parent, node_name=None):
        '''visit a node and return a AssName node'''
        newnode = new.AssName()
        self._set_infos(node, newnode, parent)
        newnode.name = node_name
        self._save_assignment(newnode)
        return newnode

    def visit_augassign(self, node, parent):
        """visit a AugAssign node by returning a fresh instance of it"""
        newnode = new.AugAssign()
        _lineno_parent(node, newnode, parent)
        newnode.op = _BIN_OP_CLASSES[node.op.__class__] + "="
        self.asscontext = "Ass"
        newnode.target = self.visit(node.target, newnode)
        self.asscontext = None
        newnode.value = self.visit(node.value, newnode)
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_backquote(self, node, parent):
        """visit a Backquote node by returning a fresh instance of it"""
        newnode = new.Backquote()
        _lineno_parent(node, newnode, parent)
        newnode.value = self.visit(node.value, newnode)
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_binop(self, node, parent):
        """visit a BinOp node by returning a fresh instance of it"""
        newnode = new.BinOp()
        _lineno_parent(node, newnode, parent)
        newnode.left = self.visit(node.left, newnode)
        newnode.right = self.visit(node.right, newnode)
        newnode.op = _BIN_OP_CLASSES[node.op.__class__]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_boolop(self, node, parent):
        """visit a BoolOp node by returning a fresh instance of it"""
        newnode = new.BoolOp()
        _lineno_parent(node, newnode, parent)
        newnode.values = [self.visit(child, newnode) for child in node.values]
        newnode.op = _BOOL_OP_CLASSES[node.op.__class__]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_callfunc(self, node, parent):
        """visit a CallFunc node by returning a fresh instance of it"""
        newnode = new.CallFunc()
        _lineno_parent(node, newnode, parent)
        newnode.func = self.visit(node.func, newnode)
        newnode.args = [self.visit(child, newnode) for child in node.args]
        newnode.starargs = self.visit(node.starargs, newnode)
        newnode.kwargs = self.visit(node.kwargs, newnode)
        newnode.args.extend(self.visit(child, newnode) for child in node.keywords)
        newnode.set_line_info(newnode.last_child())
        return newnode

    def _visit_class(self, node, parent):
        """visit a Class node by returning a fresh instance of it"""
        newnode = new.Class(node.name, None)
        _lineno_parent(node, newnode, parent)
        _init_set_doc(node, newnode)
        newnode.bases = [self.visit(child, newnode) for child in node.bases]
        newnode.body = [self.visit(child, newnode) for child in node.body]
        if 'decorator_list' in node._fields and node.decorator_list:# py >= 2.6
            newnode.decorators = self.visit_decorators(node, newnode)
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_compare(self, node, parent):
        """visit a Compare node by returning a fresh instance of it"""
        newnode = new.Compare()
        _lineno_parent(node, newnode, parent)
        newnode.left = self.visit(node.left, newnode)
        newnode.ops = [(_CMP_OP_CLASSES[op.__class__], self.visit(expr, newnode))
                    for (op, expr) in zip(node.ops, node.comparators)]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_comprehension(self, node, parent):
        """visit a Comprehension node by returning a fresh instance of it"""
        newnode = new.Comprehension()
        _lineno_parent(node, newnode, parent)
        self.asscontext = "Ass"
        newnode.target = self.visit(node.target, newnode)
        self.asscontext = None
        newnode.iter = self.visit(node.iter, newnode)
        newnode.ifs = [self.visit(child, newnode) for child in node.ifs]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_decorators(self, node, parent):
        """visit a Decorators node by returning a fresh instance of it"""
        # /!\ node is actually a _ast.Function node while
        # parent is a astng.nodes.Function node
        newnode = new.Decorators()
        _lineno_parent(node, newnode, parent)
        if 'decorators' in node._fields: # py < 2.6, i.e. 2.5
            decorators = node.decorators
        else:
            decorators= node.decorator_list
        newnode.nodes = [self.visit(child, newnode) for child in decorators]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_delete(self, node, parent):
        """visit a Delete node by returning a fresh instance of it"""
        newnode = new.Delete()
        _lineno_parent(node, newnode, parent)
        self.asscontext = "Del"
        newnode.targets = [self.visit(child, newnode) for child in node.targets]
        self.asscontext = None
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_dict(self, node, parent):
        """visit a Dict node by returning a fresh instance of it"""
        newnode = new.Dict()
        _lineno_parent(node, newnode, parent)
        newnode.items = [(self.visit(key, newnode), self.visit(value, newnode))
                          for key, value in zip(node.keys, node.values)]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_dictcomp(self, node, parent):
        """visit a DictComp node by returning a fresh instance of it"""
        newnode = new.DictComp()
        _lineno_parent(node, newnode, parent)
        newnode.key = self.visit(node.key, newnode)
        newnode.value = self.visit(node.value, newnode)
        newnode.generators = [self.visit(child, newnode)
                              for child in node.generators]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_discard(self, node, parent):
        """visit a Discard node by returning a fresh instance of it"""
        newnode = new.Discard()
        _lineno_parent(node, newnode, parent)
        newnode.value = self.visit(node.value, newnode)
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_excepthandler(self, node, parent):
        """visit an ExceptHandler node by returning a fresh instance of it"""
        newnode = new.ExceptHandler()
        _lineno_parent(node, newnode, parent)
        newnode.type = self.visit(node.type, newnode)
        if node.name is not None:
            # /!\ node.name can be a tuple
            self.asscontext = "Ass"
            newnode.name = self.visit(node.name, newnode)
            self.asscontext = None
        newnode.body = [self.visit(child, newnode) for child in node.body]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_exec(self, node, parent):
        """visit an Exec node by returning a fresh instance of it"""
        newnode = new.Exec()
        _lineno_parent(node, newnode, parent)
        newnode.expr = self.visit(node.body, newnode)
        newnode.globals = self.visit(node.globals, newnode)
        newnode.locals = self.visit(node.locals, newnode)
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_extslice(self, node, parent):
        """visit an ExtSlice node by returning a fresh instance of it"""
        newnode = new.ExtSlice()
        _lineno_parent(node, newnode, parent)
        newnode.dims = [self.visit(dim, newnode) for dim in node.dims]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_for(self, node, parent):
        """visit a For node by returning a fresh instance of it"""
        newnode = new.For()
        _lineno_parent(node, newnode, parent)
        self.asscontext = "Ass"
        newnode.target = self.visit(node.target, newnode)
        self.asscontext = None
        newnode.iter = self.visit(node.iter, newnode)
        newnode.body = [self.visit(child, newnode) for child in node.body]
        newnode.orelse = [self.visit(child, newnode) for child in node.orelse]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_from(self, node, parent):
        """visit a From node by returning a fresh instance of it"""
        names = [(alias.name, alias.asname) for alias in node.names]
        newnode = new.From(node.module or '', names, node.level)
        self._set_infos(node, newnode, parent)
        self._store_from_node(newnode)

        return newnode

    def _visit_function(self, node, parent):
        """visit a Function node by returning a fresh instance of it"""
        newnode = new.Function(node.name, None)
        _lineno_parent(node, newnode, parent)
        _init_set_doc(node, newnode)
        newnode.args = self.visit(node.args, newnode)
        newnode.body = [self.visit(child, newnode) for child in node.body]
        if 'decorators' in node._fields: # py < 2.6
            attr = 'decorators'
        else:
            attr = 'decorator_list'
        decorators = getattr(node, attr)
        if decorators:
            newnode.decorators = self.visit_decorators(node, newnode)
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_genexpr(self, node, parent):
        """visit a GenExpr node by returning a fresh instance of it"""
        newnode = new.GenExpr()
        _lineno_parent(node, newnode, parent)
        newnode.elt = self.visit(node.elt, newnode)
        newnode.generators = [self.visit(child, newnode) for child in node.generators]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_getattr(self, node, parent):
        """visit a Getattr node by returning a fresh instance of it"""
        if self.asscontext == "Del":
            # FIXME : maybe we should reintroduce and visit_delattr ?
            # for instance, deactivating asscontext
            newnode = new.DelAttr()
        elif self.asscontext == "Ass":
            # FIXME : maybe we should call visit_assattr ?
            newnode = new.AssAttr()
            self._delayed_assattr.append(newnode)
        else:
            newnode = new.Getattr()
        _lineno_parent(node, newnode, parent)
        asscontext, self.asscontext = self.asscontext, None
        newnode.expr = self.visit(node.value, newnode)
        self.asscontext = asscontext
        newnode.attrname = node.attr
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_if(self, node, parent):
        """visit a If node by returning a fresh instance of it"""
        newnode = new.If()
        _lineno_parent(node, newnode, parent)
        newnode.test = self.visit(node.test, newnode)
        newnode.body = [self.visit(child, newnode) for child in node.body]
        newnode.orelse = [self.visit(child, newnode) for child in node.orelse]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_ifexp(self, node, parent):
        """visit a IfExp node by returning a fresh instance of it"""
        newnode = new.IfExp()
        _lineno_parent(node, newnode, parent)
        newnode.test = self.visit(node.test, newnode)
        newnode.body = self.visit(node.body, newnode)
        newnode.orelse = self.visit(node.orelse, newnode)
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_import(self, node, parent):
        """visit a Import node by returning a fresh instance of it"""
        newnode = new.Import()
        self._set_infos(node, newnode, parent)
        newnode.names = [(alias.name, alias.asname) for alias in node.names]
        # save import names in parent's locals:
        for (name, asname) in newnode.names:
            name = asname or name
            newnode.parent.set_local(name.split('.')[0], newnode)
        return newnode

    def visit_index(self, node, parent):
        """visit a Index node by returning a fresh instance of it"""
        newnode = new.Index()
        _lineno_parent(node, newnode, parent)
        newnode.value = self.visit(node.value, newnode)
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_keyword(self, node, parent):
        """visit a Keyword node by returning a fresh instance of it"""
        newnode = new.Keyword()
        _lineno_parent(node, newnode, parent)
        newnode.arg = node.arg
        newnode.value = self.visit(node.value, newnode)
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_lambda(self, node, parent):
        """visit a Lambda node by returning a fresh instance of it"""
        newnode = new.Lambda()
        _lineno_parent(node, newnode, parent)
        newnode.args = self.visit(node.args, newnode)
        newnode.body = self.visit(node.body, newnode)
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_list(self, node, parent):
        """visit a List node by returning a fresh instance of it"""
        newnode = new.List()
        _lineno_parent(node, newnode, parent)
        newnode.elts = [self.visit(child, newnode) for child in node.elts]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_listcomp(self, node, parent):
        """visit a ListComp node by returning a fresh instance of it"""
        newnode = new.ListComp()
        _lineno_parent(node, newnode, parent)
        newnode.elt = self.visit(node.elt, newnode)
        newnode.generators = [self.visit(child, newnode)
                              for child in node.generators]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_module(self, node, modname, package):
        """visit a Module node by returning a fresh instance of it"""
        newnode = new.Module(modname, None)
        newnode.package = package
        _lineno_parent(node, newnode, parent=None)
        _init_set_doc(node, newnode)
        newnode.body = [self.visit(child, newnode) for child in node.body]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_name(self, node, parent):
        """visit a Name node by returning a fresh instance of it"""
        if node.id in CONST_NAME_TRANSFORMS:
            newnode = new.Const(CONST_NAME_TRANSFORMS[node.id])
            self._set_infos(node, newnode, parent)
            return newnode
        if self.asscontext == "Del":
            newnode = new.DelName()
        elif self.asscontext is not None: # Ass
            assert self.asscontext == "Ass"
            newnode = new.AssName()
        else:
            newnode = new.Name()
        _lineno_parent(node, newnode, parent)
        newnode.name = node.id
        # XXX REMOVE me :
        if self.asscontext in ('Del', 'Ass'): # 'Aug' ??
            self._save_assignment(newnode)
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_bytes(self, node, parent):
        """visit a Bytes node by returning a fresh instance of Const"""
        newnode = new.Const(node.s)
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_num(self, node, parent):
        """visit a Num node by returning a fresh instance of Const"""
        newnode = new.Const(node.n)
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_str(self, node, parent):
        """visit a Str node by returning a fresh instance of Const"""
        newnode = new.Const(node.s)
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_print(self, node, parent):
        """visit a Print node by returning a fresh instance of it"""
        newnode = new.Print()
        _lineno_parent(node, newnode, parent)
        newnode.nl = node.nl
        newnode.dest = self.visit(node.dest, newnode)
        newnode.values = [self.visit(child, newnode) for child in node.values]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_raise(self, node, parent):
        """visit a Raise node by returning a fresh instance of it"""
        newnode = new.Raise()
        _lineno_parent(node, newnode, parent)
        newnode.exc = self.visit(node.type, newnode)
        newnode.inst = self.visit(node.inst, newnode)
        newnode.tback = self.visit(node.tback, newnode)
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_return(self, node, parent):
        """visit a Return node by returning a fresh instance of it"""
        newnode = new.Return()
        _lineno_parent(node, newnode, parent)
        newnode.value = self.visit(node.value, newnode)
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_set(self, node, parent):
        """visit a Tuple node by returning a fresh instance of it"""
        newnode = new.Set()
        _lineno_parent(node, newnode, parent)
        newnode.elts = [self.visit(child, newnode) for child in node.elts]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_setcomp(self, node, parent):
        """visit a SetComp node by returning a fresh instance of it"""
        newnode = new.SetComp()
        _lineno_parent(node, newnode, parent)
        newnode.elt = self.visit(node.elt, newnode)
        newnode.generators = [self.visit(child, newnode)
                              for child in node.generators]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_slice(self, node, parent):
        """visit a Slice node by returning a fresh instance of it"""
        newnode = new.Slice()
        _lineno_parent(node, newnode, parent)
        newnode.lower = self.visit(node.lower, newnode)
        newnode.upper = self.visit(node.upper, newnode)
        newnode.step = self.visit(node.step, newnode)
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_subscript(self, node, parent):
        """visit a Subscript node by returning a fresh instance of it"""
        newnode = new.Subscript()
        _lineno_parent(node, newnode, parent)
        subcontext, self.asscontext = self.asscontext, None
        newnode.value = self.visit(node.value, newnode)
        newnode.slice = self.visit(node.slice, newnode)
        self.asscontext = subcontext
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_tryexcept(self, node, parent):
        """visit a TryExcept node by returning a fresh instance of it"""
        newnode = new.TryExcept()
        _lineno_parent(node, newnode, parent)
        newnode.body = [self.visit(child, newnode) for child in node.body]
        newnode.handlers = [self.visit(child, newnode) for child in node.handlers]
        newnode.orelse = [self.visit(child, newnode) for child in node.orelse]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_tryfinally(self, node, parent):
        """visit a TryFinally node by returning a fresh instance of it"""
        newnode = new.TryFinally()
        _lineno_parent(node, newnode, parent)
        newnode.body = [self.visit(child, newnode) for child in node.body]
        newnode.finalbody = [self.visit(n, newnode) for n in node.finalbody]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_tuple(self, node, parent):
        """visit a Tuple node by returning a fresh instance of it"""
        newnode = new.Tuple()
        _lineno_parent(node, newnode, parent)
        newnode.elts = [self.visit(child, newnode) for child in node.elts]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_unaryop(self, node, parent):
        """visit a UnaryOp node by returning a fresh instance of it"""
        newnode = new.UnaryOp()
        _lineno_parent(node, newnode, parent)
        newnode.operand = self.visit(node.operand, newnode)
        newnode.op = _UNARY_OP_CLASSES[node.op.__class__]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_while(self, node, parent):
        """visit a While node by returning a fresh instance of it"""
        newnode = new.While()
        _lineno_parent(node, newnode, parent)
        newnode.test = self.visit(node.test, newnode)
        newnode.body = [self.visit(child, newnode) for child in node.body]
        newnode.orelse = [self.visit(child, newnode) for child in node.orelse]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_with(self, node, parent):
        """visit a With node by returning a fresh instance of it"""
        newnode = new.With()
        _lineno_parent(node, newnode, parent)
        newnode.expr = self.visit(node.context_expr, newnode)
        self.asscontext = "Ass"
        newnode.vars = self.visit(node.optional_vars, newnode)
        self.asscontext = None
        newnode.body = [self.visit(child, newnode) for child in node.body]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_yield(self, node, parent):
        """visit a Yield node by returning a fresh instance of it"""
        newnode = new.Yield()
        _lineno_parent(node, newnode, parent)
        newnode.value = self.visit(node.value, newnode)
        newnode.set_line_info(newnode.last_child())
        return newnode


class TreeRebuilder3k(TreeRebuilder):
    """extend and overwrite TreeRebuilder for python3k"""

    def visit_arg(self, node, parent):
        """visit a arg node by returning a fresh AssName instance"""
        # the <arg> node is coming from py>=3.0, but we use AssName in py2.x
        # XXX or we should instead introduce a Arg node in astng ?
        return self.visit_assname(node, parent, node.arg)

    def visit_excepthandler(self, node, parent):
        """visit an ExceptHandler node by returning a fresh instance of it"""
        newnode = new.ExceptHandler()
        _lineno_parent(node, newnode, parent)
        newnode.type = self.visit(node.type, newnode)
        if node.name is not None:
            newnode.name = self.visit_assname(node, newnode, node.name)
        newnode.body = [self.visit(child, newnode) for child in node.body]
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_nonlocal(self, node, parent):
        """visit a Nonlocal node and return a new instance of it"""
        newnode = new.Nonlocal(node.names)
        self._set_infos(node, newnode, parent)
        return newnode

    def visit_raise(self, node, parent):
        """visit a Raise node by returning a fresh instance of it"""
        newnode = new.Raise()
        _lineno_parent(node, newnode, parent)
        # no traceback; anyway it is not used in Pylint
        newnode.exc = self.visit(node.exc, newnode)
        newnode.cause = self.visit(node.cause, newnode)
        newnode.set_line_info(newnode.last_child())
        return newnode

    def visit_starred(self, node, parent):
        """visit a Starred node and return a new instance of it"""
        newnode = new.Starred()
        _lineno_parent(node, newnode, parent)
        newnode.value = self.visit(node.value, newnode)
        newnode.set_line_info(newnode.last_child())
        return newnode


if sys.version_info >= (3, 0):
    TreeRebuilder = TreeRebuilder3k


