from naval import *
import unittest


class Test(unittest.TestCase):
    #TODO: test for Length, MoveTo, Regex

    def test_type(self):
        #testing the Type validator
        self.assertEqual(
            Type(int, float).validate(3.14),
            3.14
        )

        self.assertRaises(ValidationError, Type(object).validate, [])

        self.assertEqual(Type(object, subclasses=True).validate([]), [])

        schema = Schema(['name', Type(str)])
        self.assertEqual(
            schema.validate({'name': 'Marcel'}),
            {'name': 'Marcel'}
        )
        with self.assertRaises(ValidationError) as cm:
            schema.validate({'name': 2})

    def test_range(self):
        for x in (-2, 0, 2):
            self.assertEqual(Range(-3,3).validate(x), x)

        for x in (-4, 4):
            self.assertRaises(ValidationError, Range(-3,3).run, x)

        for rang, inside, outside in (
            (Range(min=7), 8, 6),
            (Range(max=7), 6, 8)
        ):
            self.assertEqual(inside, rang.validate(inside))
            self.assertRaises(ValidationError, rang.validate, outside)

    def test_optional(self):
        schema = Schema(
            ['phone number', Optional, Type(str)]
        )
        with self.assertRaises(ValidationError):
            schema.validate({'phone number': 2})
        self.assertEqual(schema.validate({}), {})

    def test_unexpected_keys(self):
        dct = {'favorite color': 'blue'}
        with self.assertRaises(ValidationError):
            Schema().validate(dct)
        self.assertEqual(Schema(unexpected_keys = Schema.KEEP).validate(dct), dct)
        self.assertEqual(Schema(unexpected_keys = Schema.DELETE).validate(dct), {})
    
    def test_default(self):
        schema = Schema(
            ['delivery method', Default('catapult'), Type(str)]
        )
        self.assertEqual(schema.validate({}), {'delivery method': 'catapult'})
        self.assertEqual(
            schema.validate({'delivery method': 'flying giraffe'}),
            {'delivery method': 'flying giraffe'}
        )
        with self.assertRaises(ValidationError):
            schema.validate({'delivery method': 2})

        schema = Schema(
            ['email', Email],
            ['username', Default(lambda d: d['email'])]
        )
    
        self.assertEqual(
            schema.validate({'email': 'contact@example.com'}),
            {'email': 'contact@example.com', 'username': 'contact@example.com'}
        )

    def test_email(self):

        self.assertRaises(ValidationError, Email.validate, 'root@localhost')
        self.assertEqual(
            Email.validate('a.b-c_@01-ex.example.org'),
            'a.b-c_@01-ex.example.org'
        )

        schema = Schema(['email', Email])
        dct1 = {'email': 'blabablalblb'}
        dct2 = {'email': 'contact@example.org'}
        dct3 = {'email': "no space@example.org"}
        for d in (dct1, dct3):
            with self.assertRaises(ValidationError) as cm:
                schema.validate(d)
            self.assertEqual(
                cm.exception.error_details,
                {'email': "This is not a valid email address."}
            )
        self.assertEqual(schema.validate(dct2), dct2)

    def test_url(self):
        schema = Schema(['url', Url])
        # test urls taken from https://mathiasbynens.be/demo/url-regex
        for url in (
            'http://foo.com/blah_blah',
            'http://foo.com/blah_blah/',
            'http://foo.com/blah_blah_(wikipedia)',
            'http://foo.com/blah_blah_(wikipedia)_(again)',
            'http://www.example.com/wpstyle/?p=364',
            'https://www.example.com/foo/?bar=baz&inga=42&quux',
            'http://142.42.1.1/',
            'http://142.42.1.1:8080/',
            'http://foo.com/blah_(wikipedia)#cite-1',
            'http://foo.com/blah_(wikipedia)_blah#cite-1',
            'http://foo.com/(something)?after=parens',
            'http://code.google.com/events/#&product=browser',
            'http://j.mp',
            'ftp://foo.bar/baz',
            'http://foo.bar/?q=Test%20URL-encoded%20stuff',
            'http://1337.net',
            'http://a.b-c.de',
            'http://223.255.255.254'
        ):
            self.assertEqual(schema.validate({'url': url}), {'url': url})
        
        for url in (
            'http://',
            'http://.',
            'http://..',
            'http://../',
            'http://?',
            'http://??',
            'http://??/',
            'http://#',
            'http://##',
            'http://##/',
            'http://foo.bar?q=Spaces should be encoded',
            '//',
            '//a',
            '///a',
            '///',
            'http:///a',
            'foo.com',
            'rdar://1234',
            'h://test',
            'http:// shouldfail.com',
            ':// should fail',
            'http://foo.bar/foo(bar)baz quux',
            'ftps://foo.bar/',
            'http://-error-.invalid/',
            'http://a.b--c.de/',
            'http://-a.b.co',
            'http://a.b-.co',
            'http://0.0.0.0',
            'http://10.1.1.0',
            'http://10.1.1.255',
            'http://224.1.1.1',
            'http://1.1.1.1.1',
            'http://123.123.123',
            'http://3628126748',
            'http://.www.foo.bar/',
            'http://www.foo.bar./',
            'http://.www.foo.bar./',
            'http://10.1.1.1',
            'http://localhost/'
        ):
            self.assertRaises(ValidationError, schema.validate, {'url': url})
    
    def test_save(self):
        # Testing Save and the callable filter
        schema = Schema(['name', str.lower])
        # shouldn't modify the document unless Save is at the end of the chain
        self.assertEqual(
            schema.validate({'name': 'Marcel'}),
            {'name': 'Marcel'}
        )
        schema = Schema(['name', str.lower, Save])
        self.assertEqual(
            schema.validate({'name': 'Marcel'}),
            {'name': 'marcel'}
        )

    def test_save_whole_document(self):
        schema = Schema(
            [lambda d: dict((k,v.upper()) for k,v in d.items()), Save],
            unexpected_keys = Schema.KEEP
        )
        dct = {'country': 'italy'} 
        self.assertEqual(schema.validate(dct), {'country': 'ITALY'})
        # shouldn't modify the original
        self.assertEqual(dct, {'country': 'italy'})

    def test_save_as(self):
        # testing SaveAs, collection validator, and the callable filter
        schema = Schema(
            ['country_alpha3', ['DEU', 'FRA', 'ITA']],
            ['country_alpha3', 
                {
                    'DEU': 'Germany',
                    'FRA': 'France',
                    'ITA': 'Italy'
                }.get,
                SaveAs('country')
            ]
        )
        self.assertEqual(
            schema.validate({'country_alpha3': 'ITA'}),
            {'country_alpha3': 'ITA', 'country': 'Italy'}
        )

    def test_delete_and_save_as(self):
        schema = Schema(
            [lambda d: d['firstname'] + ' ' + d['lastname'], SaveAs('fullname')],
            ['firstname', Delete], 
            ['lastname', Delete]
        )
        self.assertEqual(
            schema.validate({'firstname': 'Zinedine', 'lastname': 'Newton'}),
            {'fullname': 'Zinedine Newton'}
        )

    def test_assert(self):
        palindrome = Assert(
            lambda s: all(s[i] == s[len(s)-1-i] for i in range(len(s)//2)),
            "This is not a palindrome."

        )
        schema = Schema(*(
            [field, str.lower, palindrome] for field in ('test1', 'test2', 'test3')
        ))
        with self.assertRaises(ValidationError) as cm:
            schema.validate({
                'test1': 'rotator',
                'test2': 'Torino',
                'test3': 'Callac'
            })
        self.assertEqual(
            cm.exception.error_details,
            {'test2': "This is not a palindrome."}
        )

    def test_i18n(self):
        schema = Schema(['name'], ['email'])
        with self.assertRaises(ValidationError) as cm:
            schema.validate({'name': 'marcel'}, lang='fr')
        self.assertEqual(
            cm.exception.error_details['email'],
            "Champ manquant."
        )

    def test_each(self):
        schema = Schema(
            ['authors',
                Type(list, tuple),
                Length(max=10),
                Each(
                    Do( Type(str), str.title )
                ),
                Save
            ]
        )
        self.assertEqual(        
            schema.validate({'authors': ['michael Garey', 'david Johnson']}),
            {'authors': ['Michael Garey', 'David Johnson']}
        )
        with self.assertRaises(ValidationError) as cm:
            schema.validate({'authors': ['Douglas Adams', 42]})

    

if __name__ == '__main__':
    unittest.main()





