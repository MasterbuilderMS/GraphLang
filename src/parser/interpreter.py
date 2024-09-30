import re
import json
import pyperclip
import copy


class GraphLangInterpreter:
    def __init__(self, code):
        self.code: str = code
        self.tokens: list = []
        self.stack: list = []  # stack for loading operations
        self.precedence: dict = {}  # precedence of operations
        self.line_nr: int = 0
        self.output: dict = {}
        self.expression_id: int = 0
        self.token_patterns: list[tuple[str, str]] = [
            ("keyword", r"fn|ns|if|for"),
            ("identifier", r"[A-Za-z_][A-Za-z0-9_]*"),
            ("literal", r"\d+"),
            ("punctuation", r"[\{\}\[\]\(\)\.\,\;]"),
            ("operator", r"\+|-|\*|/|->|>|<|>=|<=|!=|="),
            ("skip", r"[ \t\n]+"),
            ("comment", r"#.*"),
            # ("line", r"\n")
        ]
        self.lex()
        self.current_token: tuple = self.tokens[0]
        self.position = 0
        print(f"Tokens: {self.tokens}")

    # lexer

    def lex(self):
        token_regex = '|'.join(
            f'(?P<{pair[0]}>{pair[1]})' for pair in self.token_patterns)
        matcher = re.compile(token_regex).match(self.code)
        while matcher is not None:
            token_type = matcher.lastgroup
            value = matcher.group(token_type)
            if token_type == "literal":
                value = int(value)
                self.tokens.append((token_type, value))
            elif token_type == "skip":
                pass
            else:
                self.tokens.append((token_type, value))
            self.position = matcher.end()
            matcher = re.compile(token_regex).match(self.code, self.position)

        if self.position != len(self.code):
            self.raise_error(f"Unknown character: {self.code[self.position]} at {self.line_nr}: {self.position}")  # nopep8

    # ======= Utility functions =======
    # functions that are used to navigate the token list,
    # control the stack, and raise errors

    def run(self):
        self.parse_program()

    def raise_error(self, message):
        raise ValueError(self.line_nr, ": ", message)

    # get the next token
    def next_token(self):
        try:
            self.current_token = self.tokens[self.position + 1]
            self.position += 1
            print(self.current_token)
        except IndexError:
            self.current_token = None

    # ====== Parsing statements ========
    # functions for checking that each token conforms with the grammar
    # each function returns true or false

    def parse_program(self):
        self.position = 0
        if not self.parse_statement():
            self.raise_error("Expected statement")
        # until end of program
        while self.current_token is not None:
            if (not self.parse_statement()) and (self.current_token[0] != "line"):
                self.raise_error("aExpected statement")

        data = json.dumps(self.output)
        pyperclip.copy(data)
        print("Copied: ", data)

    def parse_statement(self):
        print(f"current token at start of statement: {self.current_token}")
        if not self.parse_namespace() and not self.parse_function() and not self.parse_expression():
            self.raise_error("Expected expression")
        self.next_token()
        return True

    def parse_namespace(self):
        if self.current_token[1] != "ns":
            return False
        self.next_token()

        if self.current_token[0] != "identifier":
            return False
        self.next_token()
        if self.current_token[1] != "{":
            return False
        self.next_token()
        try:
            while self.current_token[1] != "}":
                if not self.parse_statement():
                    self.raise_error("Expected Statement")
        except TypeError:
            pass
        return True

    def parse_function(self):
        return False

    def parse_expression(self):
        if not self.parse_value():
            return False
        if self.parse_operator():
            self.parse_expression()
        return True

    def parse_value(self):
        if self.current_token[0] not in ["identifier", "literal"]:
            return False
        self.next_token()
        return True

    def parse_operator(self):
        if self.current_token[1] not in ["=", "-", "+", "/", "*"]:
            return False
        self.next_token()
        return True


a = GraphLangInterpreter('''
    ns Rectangle{
                         x = 1   
                        }




        ''')

a.run()
