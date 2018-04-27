from __future__ import absolute_import, unicode_literals

from django.test import SimpleTestCase
from eulxml.xpath import parse as parse_xpath

from corehq.apps.case_search.filter_dsl import build_filter_from_ast


class TestFilterDsl(SimpleTestCase):
    maxDiff = None

    def test_simple_filter(self):
        parsed = parse_xpath("name = 'farid'")
        expected_filter = {
            "nested": {
                "path": "case_properties",
                "query": {
                    "filtered": {
                        "query": {
                            "match_all": {}
                        },
                        "filter": {
                            "and": [
                                {
                                    "term": {
                                        "case_properties.key": "name"
                                    }
                                },
                                {
                                    "term": {
                                        "case_properties.value.exact": "farid"
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        }
        built_filter = build_filter_from_ast(parsed)
        self.assertEqual(expected_filter, built_filter)

    def test_date_comparison(self):
        parsed = parse_xpath("dob >= '2017-02-12'")
        expected_filter = {
            "nested": {
                "path": "case_properties",
                "query": {
                    "filtered": {
                        "filter": {
                            "term": {
                                "case_properties.key": "dob"
                            }
                        },
                        "query": {
                            "range": {
                                "case_properties.value_date": {
                                    "gte": "2017-02-12",
                                }
                            }
                        }
                    }
                }
            }
        }
        self.assertEqual(expected_filter, build_filter_from_ast(parsed))

    def test_numeric_comparison(self):
        parsed = parse_xpath("number <= '100.32'")
        expected_filter = {
            "nested": {
                "path": "case_properties",
                "query": {
                    "filtered": {
                        "filter": {
                            "term": {
                                "case_properties.key": "number"
                            }
                        },
                        "query": {
                            "range": {
                                "case_properties.value_numeric": {
                                    "lte": 100.32,
                                }
                            }
                        }
                    }
                }
            }
        }
        self.assertEqual(expected_filter, build_filter_from_ast(parsed))

    def test_nested_filter(self):
        parsed = parse_xpath("(name = 'farid' or name = 'leila') and dob <= '2017-02-11'")
        expected_filter = {
            "and": [
                {
                    "or": [
                        {
                            "nested": {
                                "path": "case_properties",
                                "query": {
                                    "filtered": {
                                        "query": {
                                            "match_all": {
                                            }
                                        },
                                        "filter": {
                                            "and": [
                                                {
                                                    "term": {
                                                        "case_properties.key": "name"
                                                    }
                                                },
                                                {
                                                    "term": {
                                                        "case_properties.value.exact": "farid"
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                }
                            }
                        },
                        {
                            "nested": {
                                "path": "case_properties",
                                "query": {
                                    "filtered": {
                                        "query": {
                                            "match_all": {
                                            }
                                        },
                                        "filter": {
                                            "and": [
                                                {
                                                    "term": {
                                                        "case_properties.key": "name"
                                                    }
                                                },
                                                {
                                                    "term": {
                                                        "case_properties.value.exact": "leila"
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                }
                            }
                        }
                    ]
                },
                {
                    "nested": {
                        "path": "case_properties",
                        "query": {
                            "filtered": {
                                "filter": {
                                    "term": {
                                        "case_properties.key": "dob"
                                    }
                                },
                                "query": {
                                    "range": {
                                        "case_properties.value_date": {
                                            "lte": "2017-02-11"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            ]
        }

        built_filter = build_filter_from_ast(parsed)
        self.assertEqual(expected_filter, built_filter)
