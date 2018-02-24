'''Testing of the fingerprint generation and checking'''

import unittest
from murmeli.fingerprints import FingerprintChecker


class FingerprintTest(unittest.TestCase):
    '''Tests for the key fingerprints'''

    def test_raw_fingerprints(self):
        '''Check all combinations of the following three fingerprints for their correct answer'''
        finger1 = "776034AEB5AD7A6FF668E2DD0C2C0FC8ED5118F6"
        finger2 = "4DA0047805B862B90467AD2B886A6C843297E297"
        finger3 = "3170224BCD5760F16C3A64F2CED5C733012854DB"
        self._test_finger_pair(finger1, finger2, 0)
        self._test_finger_pair(finger1, finger3, 2)
        self._test_finger_pair(finger2, finger3, 0)
        self._test_finger_pair(finger2, finger1, 1)
        self._test_finger_pair(finger3, finger1, 1)
        self._test_finger_pair(finger3, finger2, 0)

    def _test_finger_pair(self, finger1, finger2, expected_answer):
        '''Internal helper method to check the correct answer for the given print pair'''
        checker = FingerprintChecker(finger1, finger2)
        self.assertEqual(checker.get_correct_answer(), expected_answer, "Answer didn't match")
        # Use the other person's checker to get their word sequence
        other_checker = FingerprintChecker(finger2, finger1)
        words1 = other_checker.get_code_words(True, 0, "en")
        words2 = checker.get_code_words(False, expected_answer, "en")
        # Check that our calculated answer is the same as theirs
        self.assertEqual(words1, words2, "word sequences don't match")

if __name__ == "__main__":
    unittest.main()
