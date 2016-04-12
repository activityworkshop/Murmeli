# Part of Murmeli, copyright activityworkshop.net and released under GPL

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
		if self.valid:
			for l in (self.finger1 + self.finger2):
				if l not in "0123456789ABCDEF":
					self.valid = False
		self.codes = self._generateCodes(self.finger1, self.finger2)
		self.wrongCodes1 = self._generateCodes(finger1, finger2[-1] + finger2[:-1])
		self.wrongCodes2 = self._generateCodes(finger1, finger2[1:] + finger2[0])

	def _generateCodes(self, finger1, finger2):
		'''Generate the codes for the given pair of fingerprints'''
		codes = []
		if self.valid:
			for p in range(20):
				n1 = int(finger1[p*2:p*2+2], 16) # parse using base 16
				n2 = int(finger2[p*2:p*2+2], 16)
				codes.append(n1 ^ n2)
		return codes

	def _getIndexes(self, codes, ownSet = True):
		'''Generate a list of word indexes, either for myself or for the other party'''
		if not codes:
			return None
		startPos = 0 if (ownSet ^ self.am_requester) else 2
		return [codes[i*4 + startPos] for i in range(5)]

	def _getCombinationIndex(self):
		'''Return a combination index from 0 to 5, determining the order in which
		   the possible answers are displayed - 012 021 102 120 201 210'''
		if not self.codes:
			return 0
		return (self.codes[1] + self.codes[3] + self.codes[5] + (1 if self.am_requester else 0)) % 6

	def _getWords(self, indexes, ownSet, lang):
		'''Return the words for the given set (ours or not) and language (2-letter code)'''
		# Load text file for lang
		wordFile = os.path.join("lang", "codewords-" + lang + ".txt")
		if not os.path.exists(wordFile):
			wordFile = os.path.join("..", wordFile)
		with open(wordFile, "r") as f:
			words = [i[:-1] for i in f] # remove trailing linefeed character
			# Pull out the texts with the indexes and join with " "
			if indexes:
				return " ".join([words[i] for i in indexes])

	def _getComboIndexes(self):
		'''Based on the combination index, return a list showing the order in which
		   the three options should be shown'''
		i = self._getCombinationIndex()
		if i == 0: return [0, 1, 2]
		if i == 1: return [0, 2, 1]
		if i == 2: return [1, 0, 2]
		if i == 3: return [1, 2, 0]
		if i == 4: return [2, 0, 1]
		return [2, 1, 0]

	def getCorrectAnswer(self):
		'''Return the correct answer expected from the check - an index 0, 1 or 2'''
		if not self.valid: return -1
		i = self._getCombinationIndex()
		return [0, 0, 1, 2, 1, 2][i]

	def getCodeWords(self, ownSet, answerIndex, lang):
		'''Return a string containing five codewords, according to the ownSet (True for own, False for not),
		   the answerIndex (0, 1 or 2 for the other party), and the language (2-letter code)'''
		if ownSet:
			indexes = self._getIndexes(self.codes, ownSet)
		else:
			# other set, so we need to use the answerIndex (0, 1 or 2)
			listIndex = self._getComboIndexes()[answerIndex]
			if listIndex == 0:
				indexes = self._getIndexes(self.codes, ownSet)
			elif listIndex == 1:
				indexes = self._getIndexes(self.wrongCodes1, ownSet)
			elif listIndex == 2:
				indexes = self._getIndexes(self.wrongCodes2, ownSet)
		return self._getWords(indexes, ownSet, lang)


if __name__ == "__main__":
	fps = ['B0C5D09F03433988892890E236ECAB5DA51C178A', 'C46A68B898C8494A317D1247DA30BB68D00BA823', 'BD0638AF686D27D9D461EE9F07A4D9D622B8562B']
	for i in fps:
		for j in fps:
			if i != j:
				checker = FingerprintChecker(i, j)
				print("own:", checker.getCodeWords(True, 0, "en"))
				print("other0:", checker.getCodeWords(False, 0, "en"))
				print("other1:", checker.getCodeWords(False, 1, "en"))
				print("other2:", checker.getCodeWords(False, 2, "en"))
				print("Correct answer is:", checker.getCorrectAnswer())
