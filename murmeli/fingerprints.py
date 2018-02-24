'''Fingerprint module, for calculating codes from key fingerprints.
   Part of Murmeli, copyright activityworkshop.net and released under the GPL v2.'''

import os

class FingerprintChecker:
    '''Class to combine a pair of key fingerprints
       and produce a pair of word lists from the dictionary'''
    def __init__(self, finger1, finger2):
        self.finger1 = finger1.upper()
        self.finger2 = finger2.upper()
        self.am_requester = self.finger1 < self.finger2
        self.valid = self.finger1 and self.finger2 \
            and self.finger1 != self.finger2 \
            and len(self.finger1) == 40 and len(self.finger2) == 40
        # Check that string only contains hex characters [0-9A-F]
        if self.valid:
            both_prints = self.finger1 + self.finger2
            for char in both_prints:
                if char not in "0123456789ABCDEF":
                    self.valid = False
        self.codes = self._generate_codes(self.finger1, self.finger2)
        self.wrong_codes1 = self._generate_codes(finger1, finger2[-1] + finger2[:-1])
        self.wrong_codes2 = self._generate_codes(finger1, finger2[1:] + finger2[0])

    def _generate_codes(self, finger1, finger2):
        '''Generate the codes for the given pair of fingerprints'''
        codes = []
        if self.valid:
            for pos in range(20):
                num1 = int(finger1[pos*2:pos*2+2], 16) # parse using base 16
                num2 = int(finger2[pos*2:pos*2+2], 16)
                codes.append(num1 ^ num2)
        return codes

    def _get_indexes(self, codes, own_set=True):
        '''Generate a list of word indexes, either for myself or for the other party'''
        if not codes:
            return None
        start_pos = 0 if (own_set ^ self.am_requester) else 2
        return [codes[i*4 + start_pos] for i in range(5)]

    def _get_combination_index(self):
        '''Return a combination index from 0 to 5, determining the order in which
           the possible answers are displayed - 012 021 102 120 201 210'''
        if not self.codes:
            return 0
        return (self.codes[1] + self.codes[3] + self.codes[5] + (1 if self.am_requester else 0)) % 6

    @staticmethod
    def _get_words_for_indexes(indexes, lang):
        '''Return the words for the given indexes and language (2-letter code)'''
        # Load text file for lang
        word_file = os.path.join("lang", "codewords-" + lang + ".txt")
        if not os.path.exists(word_file):
            word_file = os.path.join("..", word_file)
        with open(word_file, "r") as word_stream:
            words = [i[:-1] for i in word_stream] # remove trailing linefeed character
            # Pull out the texts with the indexes and join with " "
            if indexes:
                return " ".join([words[i] for i in indexes])

    def _get_combo_indexes(self):
        '''Based on the combination index, return a list showing the order in which
           the three options should be shown'''
        combo_index = self._get_combination_index()
        assert combo_index >= 0 and combo_index <= 5
        combos = [[0, 1, 2], [0, 2, 1], [1, 0, 2], [1, 2, 0], [2, 0, 1], [2, 1, 0]]
        return combos[combo_index]

    def get_correct_answer(self):
        '''Return the correct answer expected from the check - an index 0, 1 or 2'''
        if not self.valid:
            return -1
        i = self._get_combination_index()
        return [0, 0, 1, 2, 1, 2][i]

    def get_code_words(self, own_set, answer_index, lang):
        '''Return a string containing five codewords, according to the own_set flag,
           the answer_index (0, 1 or 2 for the other party), and the language (2-letter code)'''
        if own_set:
            indexes = self._get_indexes(self.codes, own_set)
        else:
            # other set, so we need to use the answer_index (0, 1 or 2)
            list_index = self._get_combo_indexes()[answer_index]
            if list_index == 0:
                indexes = self._get_indexes(self.codes, own_set)
            elif list_index == 1:
                indexes = self._get_indexes(self.wrong_codes1, own_set)
            elif list_index == 2:
                indexes = self._get_indexes(self.wrong_codes2, own_set)
        return FingerprintChecker._get_words_for_indexes(indexes, lang)
