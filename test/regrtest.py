
from logilab.common.testlib import unittest_main, TestCase

from logilab.astng import ResolveError, MANAGER as m
from logilab.astng.builder import ASTNGBuilder, build_module

import sys
from os.path import abspath
sys.path.insert(1, abspath('regrtest_data'))

class NonRegressionTC(TestCase):

##     def test_resolve1(self):
##         mod = m.astng_from_module_name('data.nonregr')
##         cls = mod['OptionParser']
##         self.assertRaises(ResolveError, cls.resolve_dotted, cls.basenames[0])
##         #self.assert_(cls is not cls.resolve_dotted(cls.basenames[0]))

    def test_module_path(self):
        mod = m.astng_from_module_name('import_package_subpackage_module')
        package = mod.igetattr('package').next()
        self.failUnlessEqual(package.name, 'package')
        subpackage = package.igetattr('subpackage').next()
        self.failUnlessEqual(subpackage.name, 'package.subpackage')
        module = subpackage.igetattr('module').next()
        self.failUnlessEqual(module.name, 'package.subpackage.module')


    def test_living_property(self):
        builder = ASTNGBuilder()
        builder._done = {}
        builder._module = sys.modules[__name__]
        builder.object_build(build_module('module_name', ''), Whatever)

    def test_new_style_class_detection(self):
        try:
            import pygtk
        except ImportError:
            self.skip('test skipped: pygtk is not available')
        else:
            builder = ASTNGBuilder()
            data = """
import pygtk
pygtk.require("2.6")
import gobject

class A(gobject.GObject):
    def __init__(self, val):
        gobject.GObject.__init__(self)
        self._val = val

    def _get_val(self):
        print "get"
        return self._val

    def _set_val(self, val):
        print "set"
        self._val = val

    val = property(_get_val, _set_val)

if __name__ == "__main__":
    print gobject.GObject.__bases__
    a = A(7)
    print a.val
    a.val = 6
    print a.val
"""
            astng = builder.string_build(data, __name__, __file__)
            a = astng['A']
            self.assert_(a.newstyle)
        
class Whatever(object):
    a = property(lambda x: x, lambda x: x)
    
if __name__ == '__main__':
    unittest_main()