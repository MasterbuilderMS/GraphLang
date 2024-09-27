import re


class GraphLangInterpreter:
    def __init__(self, code):
        self.code: str = code
        self.tokens = []
        self.stack: list = []  # stack for loading operations
        self.precedence: dict = {}  # precedence of operations
        self.current_token: tuple = None
        self.line_nr: int = 0
        self.output: dict = {}
        self.expression_id: int = 0
        self.token_patterns = [
            ("keyword", r"fn|ns|if|for"),
            ("identifier", r"[A-Za-z_][A-Za-z0-9_]*"),
            ("literal", r"\d+"),
            ("punctuation", r"[\{\}\[\]\(\)\.\,]"),
            ("operator", r"\+|-|\*|/|->|>|<|>=|<=|!=|="),
            ("skip", r"[ \t\n]+"),
            ("comment", r"#.*"),
        ]
        self.lex()

    # lexer

    def lex(self):
        position = 0
        token_regex = '|'.join(
            f'(?P<{pair[0]}>{pair[1]})' for pair in self.token_patterns)
        matcher = re.compile(token_regex).match(self.code)
        while matcher is not None:
            token_type = matcher.lastgroup
            value = matcher.group(token_type)
            print(f"matched {token_type}, {value}")
            if token_type == "literal":
                value = int(value)
            elif token_type == "skip":
                pass
            else:
                self.tokens.append((token_type, value))
            position = matcher.end()
            matcher = re.compile(token_regex).match(self.code, position)

        if position != len(self.code):
            self.raise_error(f"Unknown character: {self.code[position]} at {
                             self.line_nr}: {position}")

    def next_token(self):
        pass

    # set the current token
    def set_current_token(self):
        pass

    # expect the next token
    def expect_token(self, type: str):
        pass

    def raise_error(self, message):
        raise ValueError(self.line_nr, ": ", message)


a = GraphLangInterpreter("""ns Rectangle{12}
    fn Draw(a,b){
                         y = a + b
                         }
    y = x
    polygon ((1,1),(2,2),(1,2))
                         }





                         """)

for i in a.tokens:
    print(i)
