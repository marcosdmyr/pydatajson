import unittest
import os
import re
import json
from dateutil import parser, tz
from .context import pydatajson
from pydatajson.ckan_utils import map_dataset_to_package, map_distributions_to_resources, convert_iso_string_to_utc

SAMPLES_DIR = os.path.join("tests", "samples")


class DatasetConversionTestCase(unittest.TestCase):
    sample = 'full_data.json'

    @classmethod
    def get_sample(cls, sample_filename):
        return os.path.join(SAMPLES_DIR, sample_filename)

    @classmethod
    def setUpClass(cls):
        cls.catalog = pydatajson.DataJson(cls.get_sample(cls.sample))
        cls.dataset = cls.catalog.datasets[0]
        cls.distributions = cls.dataset['distribution']

    def test_replicated_plain_attributes_are_corrext(self):
        package = map_dataset_to_package(self.dataset)
        plain_replicated_attributes = [('title', 'title'),
                                       ('notes', 'description'),
                                       ('url', 'landingPage')]
        for fst, snd in plain_replicated_attributes:
            self.assertEqual(self.dataset.get(snd), package.get(fst))

    def test_dataset_nested_replicated_attributes_stay_the_same(self):
        package = map_dataset_to_package(self.dataset)
        contact_point_nested = [('maintainer', 'fn'),
                                ('maintainer_email', 'hasEmail')]
        for fst, snd in contact_point_nested:
            self.assertEqual(self.dataset.get('contactPoint', {}).get(snd), package.get(fst))
        publisher_nested = [('author', 'name'),
                            ('author_email', 'mbox')]
        for fst, snd in publisher_nested:
            self.assertEqual(self.dataset.get('publisher').get(snd), package.get(fst))

    def test_dataset_array_attributes_are_correct(self):
        package = map_dataset_to_package(self.dataset)
        groups = [group['name'] for group in package.get('groups', [])]
        super_themes = [re.sub(r'(\W+|-)', '', s_theme).lower() for s_theme in self.dataset.get('superTheme')]
        self.assertItemsEqual(super_themes, groups)

        tags = [tag['name'] for tag in package['tags']]
        themes_and_keywords = self.dataset.get('theme', []) + self.dataset.get('keyword', [])
        themes_and_keywords = themes_and_keywords
        self.assertItemsEqual(themes_and_keywords, tags)

    def test_dataset_extra_attributes_are_correct(self):
        package = map_dataset_to_package(self.dataset)
#       extras are included in dataset
        for extra in package['extras']:
            dataset_value = self.dataset[extra['key']]
            if type(dataset_value) is list:
                dataset_value = json.dumps(dataset_value)
            self.assertEqual(dataset_value, extra['value'])
#       dataset attributes are included in extras
        extra_attrs = ['super_theme', 'issued', 'modified', 'accrualPeriodicity', 'temporal', 'language', 'spatial']
        for key in extra_attrs:
            value = self.dataset[key]
            if type(value) is list:
                value = json.dumps(value)
            resulting_dict = {'key': key, 'value': value}
            self.assertTrue(resulting_dict in package['extras'])

    def test_resources_replicated_attributes_stay_the_same(self):
        resources = map_distributions_to_resources(self.distributions)
        for resource in resources:
            distribution = next(x for x in self.dataset['distribution'] if x['identifier'] == resource['id'])
            replicated_attributes = [('name', 'title'),
                                     ('url', 'downloadURL'),
                                     ('mimetype', 'mediaType'),
                                     ('description', 'description'),
                                     ('format', 'format'),
                                     ('size', 'byteSize')]
            for fst, snd in replicated_attributes:
                if distribution.get(snd):
                    self.assertEqual(distribution.get(snd), resource.get(fst))
                else:
                    self.assertIsNone(resource.get(fst))

    def test_resources_transformed_attributes_are_correct(self):
        resources = map_distributions_to_resources(self.distributions)
        for resource in resources:
            distribution = next(x for x in self.dataset['distribution'] if x['identifier'] == resource['id'])
            time_attributes = [('created', 'issued'), ('last_modified', 'modified')]
            for fst, snd in time_attributes:
                if distribution.get(snd):
                    dist_time = parser.parse(distribution.get(snd)).astimezone(tz.tzutc())
                    dist_time = dist_time.replace(tzinfo=None).isoformat()
                    self.assertEqual(dist_time, resource.get(fst))
                else:
                    self.assertIsNone(resource.get(fst))


if __name__ == '__main__':
    unittest.main()
