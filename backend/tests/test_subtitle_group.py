import unittest

from bonita.services.subtitle_service import subtitle_group_id


class SubtitleGroupIdTest(unittest.TestCase):
    def test_episode_groups_under_series(self):
        self.assertEqual(subtitle_group_id("episode", 12, 34), 12)

    def test_episode_without_series_stays_on_itself(self):
        self.assertEqual(subtitle_group_id("episode", None, 34), 34)

    def test_other_types_stay_on_themselves(self):
        self.assertEqual(subtitle_group_id("movie", 12, 34), 34)
        self.assertEqual(subtitle_group_id("number", None, 7), 7)
        self.assertIsNone(subtitle_group_id(None, None, None))


if __name__ == "__main__":
    unittest.main()
