# coding=utf-8


class DFA(object):
    """
    DFA算法
    """

    def __init__(self):
        self.keyword_chains = {}
        self.delimit = '\x00'
        self.skip_root = [
            ' ',
            '&',
            '!',
            '！',
            '@',
            '#',
            '$',
            '￥',
            '*',
            '^',
            '%',
            '?',
            '？',
            '<',
            '>',
            '《',
            '》',
            '\n',
            '|',
            '[',
            ']',
        ]

    def add_word(self, keyword):
        keyword = keyword.lower()
        chars = keyword.strip()
        if not chars:
            return
        level = self.keyword_chains
        for i in range(len(chars)):
            if chars[i] in level:
                level = level[chars[i]]
            else:
                if not isinstance(level, dict):
                    break
                last_level, last_char = dict(), ''
                for j in range(i, len(chars)):
                    level[chars[j]] = {}
                    last_level, last_char = level, chars[j]
                    level = level[chars[j]]
                if last_level and last_char:
                    last_level[last_char] = {
                        self.delimit: 0
                    }
                break
        if i == len(chars) - 1:
            level[self.delimit] = 0

    def remove_unused_chars(self, message):
        for x in self.skip_root:
            message = message.replace(x, '')
        return message

    def check_exist_word(self, message):
        message = self.remove_unused_chars(message.lower())
        start = 0
        res = []
        while start < len(message):
            level = self.keyword_chains
            step_ins = 0
            for char in message[start:]:
                if char in level:
                    step_ins += 1
                    if self.delimit not in level[char]:
                        level = level[char]
                    else:
                        res.append(message[start:start + step_ins])
                        start += step_ins - 1
                        break
                else:
                    break
            start += 1
        return res

    def load_words(self, file_path):
        with open(file_path, 'r') as f:
            for x in f.readlines():
                self.add_word(x.strip())


dfa = DFA()
dfa.load_words('/sanic/keywords.txt')
