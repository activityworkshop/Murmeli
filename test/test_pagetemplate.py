''''Testing of the wrapper to the Tempita templates'''

import unittest
from murmeli.pagetemplate import PageTemplate


class TemplateTest(unittest.TestCase):
    '''Tests for the basics of the page templates'''

    def test_simple_template(self):
        '''Just check that template works without substitution'''
        template = PageTemplate(None)
        template.set_template("This is just a string")
        result = template.get_html(None)
        self.assertEqual(result, "This is just a string", "output matches input")

    def test_with_tokens(self):
        '''Check that substitution of text tokens works'''
        template = PageTemplate(None)
        template.set_template("The title is '{{langs['test.title']}}'")
        tokens = {"unused.key":"mushroom", "test.title":"Pterosaur"}
        result = template.get_html(tokens=tokens)
        self.assertEqual(result, "The title is 'Pterosaur'", "output matches input")

    def test_with_params(self):
        '''Check that substitution of regular parameters works'''
        template = PageTemplate(None)
        template.set_template("My favourite dinosaur is '{{dino}}'")
        params = {"dino":"Triceratops"}
        result = template.get_html(None, params)
        self.assertEqual(result, "My favourite dinosaur is 'Triceratops'", "output matches input")

    def test_with_no_params(self):
        '''Check that nothing bad happens when no parameters are given'''
        template = PageTemplate(None)
        template.set_template("Let sleeping velociraptors lie")
        result = template.get_html({})
        self.assertEqual(result, "Let sleeping velociraptors lie", "output matches input")


if __name__ == "__main__":
    unittest.main()
