#!/usr/bin/env python3

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
        self.folder_id: int = 0
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
        self.constants = ["X", "Y", "x", "y"]  # variables allowed by desmos
        self.expression_template = None
        self.location = 0
        self.tokens.append(("line", "\n"))  # append an item to fix parsing
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

    def subscriptify(self, text):
        if len(list(text)) == 1:
            return text
        else:
            return f"{text[0]}_{{{text[1:]}}}"
    # ====== Parsing statements ========
    # functions for checking that each token conforms with the grammar
    # each function returns true or false

    def parse_program(self):
        self.expression_template = {
            "type": "expression",
            "id": 1,
            "color": "#c74440",
            "latex": "",
            "lineStyle": "SOLID",
            "lineOpacity": "1",
            "lineWidth": "2.5",
            "folderId": 0
        }
        self.folder_template = {
            "type": "folder",
            "id": 1,
            "name": ""
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

    # substatement checks if the statement is inside a function

    def parse_statement(self):
        if self.current_token == None:
            return True
        while self.current_token[0] == "line":
            self.next_token()
        self.location: list = self.output["expressions"]["list"]
        self.location.append(copy.deepcopy(self.expression_template))
        self.expression_id += 1
        self.location[-1]["id"] = self.expression_id
        self.location[-1]["folderId"] = self.folder_id
        if not self.parse_namespace() and not self.parse_function() and not self.parse_expression():
            self.raise_error("Expected expression")
        self.next_token()
        return True

    def parse_namespace(self):
        if self.current_token[1] != "ns":
            return False
        self.location[-1] = copy.deepcopy(self.folder_template)
        self.location[-1]["id"] = self.expression_id
        self.next_token()
        if self.current_token[0] != "identifier":
            return False
        self.location[-1]["title"] = self.current_token[1]
        self.folder_id = str(self.expression_id)
        self.next_token()
        if self.current_token[1] != "{":
            self.raise_error("Expected { after namespace definition")
            return False
        self.next_token()
        try:
            while self.current_token[1] != "}":
                if not self.parse_statement():
                    self.raise_error("Expected Statement inside namespace")
        except TypeError:
            pass
        self.folder_id = 0
        return True

    def parse_function(self):
        if self.current_token[1] != "fn":
            return False
        self.next_token()
        if self.current_token[0] != "identifier":
            self.raise_error("Expected function name after defintion")
            return False
        self.location[-1]["latex"] += self.subscriptify(self.current_token[1])
        self.location[-1]["latex"] += r"\left("
        self.next_token()
        if self.current_token[1] != "(":
            self.raise_error("Expected (")
            return False
        self.next_token()
        while self.current_token[1] != ")":
            if self.current_token[0] != "identifier":
                self.raise_error("Expected parameter")
                return False
            self.location[-1]["latex"] += self.subscriptify(
                self.current_token[1])
            self.next_token()
            if self.current_token[1] == ")":
                self.location[-1]["latex"] += r"\right)"
                self.next_token()
                break
            if self.current_token[1] != ",":
                self.raise_error("Expected ',' between parameters")
                return False
            self.location[-1]["latex"] += ","
            self.next_token()
        if self.current_token[1] != "{":
            self.raise_error("Expected { after function definition")
            return False

        self.location[-1]["latex"] += "="

        self.next_token()
        while self.current_token[0] in ["line", "comment"]:
            self.next_token()
        if not self.parse_expression():
            self.raise_error("Expected Statement")
        while self.current_token[0] in ["line", "comment"]:
            self.next_token()
        if self.current_token[1] != "}":
            return False

        return True

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
            if self.current_token[1] not in ["^", "=", "->", "-", "+", "/", "*", "<", ">", "<=", ">="]:
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
        sys.argv[1] = input("Input file path")
        exit()
    time.sleep(0.05)
    try:
        with open(sys.argv[1], "rt") as f:
            code = f.read()
            os.system("cls")
            for i in range(30):
                os.system("cls")
                print(colors.GREEN + "Compiling" + (" ."*i) + colors.END)
                time.sleep(0.0001)

            _ = GraphLangInterpreter(code)
            _.run()
    except FileNotFoundError:
        print(colors.RED + '''Failed to start compilation. Are you sure the file exists?''' + colors.END
              )
        exit()
