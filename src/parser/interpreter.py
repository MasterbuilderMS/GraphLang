import re
import json
import pyperclip
from Utils import colors
import sys
import time
import os
import copy


class GraphLangInterpreter:
    def __init__(self, code):
        self.code: str = code
        self.tokens: list = []
        self.stack: list = []  # stack for loading operations
        self.precedence: dict = {}  # precedence of operations
        self.vars: dict = {}  # dict of variables
        self.line_nr: int = 0
        self.output: dict = {}
        self.expression_id: int = 0
        self.token_patterns: list[tuple[str, str]] = [
            ("keyword", r"fn|ns|if|for"),
            ("identifier", r"[A-Za-z_][A-Za-z0-9_]*"),
            ("literal", r"\d+"),
            ("punctuation", r"[\{\}\[\]\(\)\.\,\;]"),
            ("operator", r"\+|-|\*|/|->|>|<|>=|<=|!=|="),
            ("skip", r"[ \t]+"),
            ("comment", r"#.*"),
            ("line", r"\n")
        ]
        self.lex()
        self.current_token: tuple = self.tokens[0]
        self.position = 0
        self.constants = ["X", "Y", "x", "y"]
        self.expression_template = None
        self.location = 0
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
            elif token_type in ["skip", "comment"]:
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
            # print(self.current_token)
        except IndexError:
            self.current_token = None

    def stack_pop(self):
        return self.stack.pop()

    def stack_push(self, value):
        return self.stack.append(value)

    # ====== Parsing statements ========
    # functions for checking that each token conforms with the grammar
    # each function returns true or false

    def parse_program(self):
        self.expression_template = {
            "type": "expression",
            "id": 1,
            "color": "#c74440",
            "latex": ""
        }
        self.output = {
            "version": 11,
            "randomSeed": "038ada9396ae4919ad0383b8fe134eb0",
            "graph": {
                "viewport": {
                    "xmin": -10,
                    "ymin": -7.595766129032258,
                    "xmax": 10,
                    "ymax": 7.595766129032258
                }
            },
            "expressions": {
                "list": []
            },
            "includeFunctionParametersInRandomSeed": True
        }
        # print(self.current_token)
        self.position = 0
        if not self.parse_statement():
            self.raise_error("Expected statement")
        # until end of program
        while self.current_token is not None:
            if self.current_token[0] != "line":
                if not self.parse_statement():
                    self.raise_error("Expected statement")
            elif self.current_token[0] == "line":
                try:
                    self.parse_statement()
                except TypeError:
                    pass

        data = json.dumps(self.output)
        pyperclip.copy(data)
        print("Copied: ", data)
        print(self.vars)

    def parse_statement(self):
        if self.current_token == None:
            return True
        while self.current_token[0] == "line":
            self.next_token()
        self.location: list = self.output["expressions"]["list"]
        self.location.append(copy.deepcopy(self.expression_template))
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

    def parse_expression(self):  # x + 1
        if not self.parse_value():
            return False
        if self.parse_operator():
            self.parse_expression()
        if self.current_token != None:
            if self.current_token[0] == "line":
                return True
        else:
            return True

    def parse_value(self):  # 1232, or x, y or hello
        if self.current_token != None:
            if self.current_token[0] not in ["identifier", "literal"]:
                return False
        else:
            return True
        self.location[-1]["latex"] += str(self.current_token[1])
        self.next_token()
        return True

    def parse_operator(self):
        if self.current_token != None:
            if self.current_token[1] not in ["=", "->", "-", "+", "/", "*"]:
                return False
        else:
            return False
        self.location[-1]["latex"] += str(self.current_token[1])
        self.next_token()
        return True


if __name__ == "__main__":
    os.system("cls")
    try:
        print(colors.BLUE + "Looking for - " + sys.argv[1] + colors.END)
        time.sleep(0.1)
    except IndexError:
        print(colors.RED + '''Failed to start compilation. Are you sure you have passed in the file?
Hint: try ''' + colors.END + colors.YELLOW + "py interpreter.py foo.graphlang" + colors.END
              )
        exit()
    time.sleep(0.05)
    try:
        with open(sys.argv[1], "rt") as f:
            code = f.read()
            os.system("cls")
            for i in range(30):
                os.system("cls")
                print(colors.GREEN + "Compiling" + (" ."*i) + colors.END)
                time.sleep(0.005)

            _ = GraphLangInterpreter(code)
            _.run()
    except FileNotFoundError:
        print(colors.RED + '''Failed to start compilation. Are you sure the file exists?''' + colors.END
              )
        exit()
