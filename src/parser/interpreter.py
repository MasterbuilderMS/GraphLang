#!/usr/bin/env python3

from Utils import colors
import re
import json
import pyperclip
import sys
import time
import os
import copy


class Error(BaseException):
    def __init__(self, message, lines: list, line_nr):
        self.message = "Syntax Error: " + message
        self.line_number = line_nr
        self.new_message = f'''
Traceback (most recent call last):
File {colors.BLUE}"<{sys.argv[1]}>"{colors.END}, line {colors.BLUE}{self.line_number}{colors.END}, in {colors.BLUE}<module>{colors.END}:
    {lines[self.line_number - 1]}
    ^'''
        for i in range(len(lines[self.line_number-1])):
            self.new_message += "^"
        self.new_message += f"\nSyntax Error: {
            colors.RED}{message}{colors.END}"
        super().__init__(self.new_message)


class GraphLangInterpreter:
    def __init__(self, code):
        self.code: str = code
        self.tokens: list = []
        self.vars: dict = {"global": []}  # dict of variables
        self.line_nr: int = 0
        self.output: dict = {}
        self.expression_id: int = 0
        self.folder_id: int = 0
        self.token_patterns: list[tuple[str, str]] = [
            ("keyword", r"fn|ns|if|for"),
            ("identifier", r"[A-Za-z_][A-Za-z0-9_]*"),
            ("literal", r"\d+"),
            ("punctuation", r"[\{\}\[\]\(\)\.\,\;]"),
            ("operator", r"\+|-|\*|/|->|>|<|>=|<=|!=|=|\^"),
            ("skip", r"[ \t]+"),
            ("note", r"\".*?\"|'.*?'"),
            ("comment", r"#.*"),
            ("line", r"\n")
        ]
        self.lex()
        self.lines = self.code.splitlines()
        try:
            self.current_token: tuple = self.tokens[0]
        except IndexError:
            self.current_token = None
        self.position = 0
        self.constants = ["X", "Y", "x", "y"]  # variables allowed by desmos
        self.expression_template = None
        self.note_template = None
        self.scope = "global"
        self.location = 0
        self.tokens.append(("line", "\n"))  # append an item to fix parsing
        self.builtins = ["sin", "cos", "tan", "csc", "sec", "cot", "arcsin", "arcos", "arctangent", "arccosecant", "arcsecant", "arccotangent", "mean", "median", "min", "max", "quartile", "quantile", "stdev", "stdevp", "varp",
                         "mad", "cov", "covp", "corr", "spearman", "stats", "count", "total", "join", "sort", "shuffle", "unique", "histogram", "dotplot", "boxplot", "random", "exp", "ln", "log", "int", "sum", "prod", "tone", "lcm", "sqrt", "polygon"]
        self.functions = []  # user functions
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
        try:
            if self.position != len(self.code):
                self.raise_error(f"Unknown character: {self.code[self.position]} at {self.line_nr}: {self.position}")  # nopep8
        except AttributeError:
            pass

    # ======= Utility functions =======
    # functions that are used to navigate the token list,
    # control the stack, and raise errors

    def run(self):
        # setup exception handling hook
        def custom_excepthook(exc_type, exc_value, exc_traceback):
            if isinstance(exc_value, Error):
                # Red text for better visibility.
                print(f"{exc_value}")
            else:
                # For other exceptions, you can still display the full traceback if needed.
                sys.__excepthook__(exc_type, exc_value, exc_traceback)

        sys.excepthook = custom_excepthook

        if len(self.tokens) == 0:
            pass
        else:
            self.line_nr += 1
            self.parse_program()

            data = json.dumps(self.output)
            pyperclip.copy(data)
            print("Copied: ", data)

    def raise_error(self, message):
        raise Error(message, self.lines, self.line_nr)

    # get the next token

    def next_token(self):
        try:
            if self.current_token[0] == "line":
                self.line_nr += 1
            self.current_token = self.tokens[self.position + 1]
            self.position += 1
            # print(self.current_token)
        except IndexError:
            self.current_token = None

    def peek_token(self, num):
        try:
            return self.tokens[self.position + num]
        except IndexError:
            pass

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
        self.note_template = {
            "type": "text",
            "id": 1,
            "text": ""
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

    # substatement checks if the statement is inside a function

    def parse_statement(self):
        if self.current_token == None:  # if there is not statement, return true
            return True
        while self.current_token[0] == "line":  # skip through extra lines
            self.next_token()
        self.location: list = self.output["expressions"]["list"]
        self.location.append(copy.deepcopy(self.expression_template))
        self.expression_id += 1
        self.location[-1]["id"] = self.expression_id
        self.location[-1]["folderId"] = self.folder_id
        if not self.parse_namespace() and not self.parse_function() and not self.parse_expression() and not self.parse_note():
            self.raise_error("Expected statement")
        self.next_token()
        return True

    def parse_note(self):
        if self.current_token[0] != "note":
            return False
        self.location.append(copy.deepcopy(self.note_template))
        self.location[-1]["text"] += str(self.current_token[1])
        self.next_token()
        return True

    def parse_namespace(self):
        if self.current_token[1] != "ns":
            return False
        self.location[-1] = copy.deepcopy(self.folder_template)
        self.location[-1]["id"] = self.expression_id
        self.next_token()
        if self.current_token[0] != "identifier":
            self.raise_error("Expected identifier")
        self.scope = self.current_token[1]
        self.location[-1]["title"] = self.current_token[1]
        self.folder_id = str(self.expression_id)
        self.next_token()
        if self.current_token[1] != "{":
            self.raise_error("Expected { after namespace definition")
        self.next_token()
        try:
            while self.current_token[1] != "}":
                if not self.parse_statement():
                    self.raise_error("Expected Statement inside namespace")
        except TypeError:
            pass
        self.folder_id = 0
        self.scope = "global"
        return True

    def parse_function(self):
        if self.current_token[1] != "fn":
            return False
        self.next_token()
        if self.current_token[0] != "identifier":
            self.raise_error("Expected function name after defintion")
        self.location[-1]["latex"] += self.subscriptify(self.current_token[1])
        self.location[-1]["latex"] += r"\left("
        self.scope = self.current_token[1]
        self.functions.append(self.current_token[1])
        self.next_token()
        if self.current_token[1] != "(":
            self.raise_error("Expected (")
        self.next_token()
        while self.current_token[1] != ")":
            if self.current_token[0] != "identifier":
                self.raise_error("Expected parameter")
            self.location[-1]["latex"] += self.subscriptify(
                self.scope + self.current_token[1])
            try:
                self.vars[self.scope] += [self.current_token[1]]
            except KeyError:
                self.vars[self.scope] = [self.current_token[1]]
            self.next_token()
            if self.current_token[1] == ")":
                self.location[-1]["latex"] += r"\right)"
                self.next_token()
                break
            if self.current_token[1] != ",":
                self.raise_error("Expected ',' between parameters")
            self.location[-1]["latex"] += ","
            self.next_token()
        if self.current_token[1] != "{":
            self.raise_error("Expected { after function definition")

        self.location[-1]["latex"] += "="

        self.next_token()
        while self.current_token[0] in ["line", "comment"]:
            self.next_token()
        if not self.parse_expression():
            self.raise_error("Expected Statement")
        while self.current_token[0] in ["line", "comment"]:
            self.next_token()
        if self.current_token[1] != "}":
            self.raise_error("'}' was not closed")
        self.scope = "global"
        return True

    def parse_expression(self):  # x + 1
        # check if it is a point first:
        # safety in case it isn't a point so we can jump back here
        return_latex = copy.deepcopy(self.location[-1]["latex"])
        return_location = copy.deepcopy(self.position)
        try:
            if not self.parse_point():
                self.position = return_location - 1
                self.location[-1]["latex"] = return_latex
            else:
                return True
        except Error:
            self.position = return_location - 1
            self.location[-1]["latex"] = return_latex
        self.next_token()
        if self.current_token[1] == "(":
            self.location[-1]["latex"] += "\\left("
            self.next_token()
            self.parse_expression()
            if self.current_token[1] != ")":
                self.raise_error("Expected )")
            else:
                self.location[-1]["latex"] += "\\right)"
                self.next_token()

        else:
            if not self.parse_function_call() and not self.parse_value() and not self.parse_list() and not self.parse_point():
                return False
            if self.parse_operator():
                self.parse_expression()

        if self.current_token != None:
            if self.current_token[0] == "line" or self.current_token[1] in [",", "]", ")"]:
                return True
        else:
            return True

    def parse_function_call(self):
        if self.current_token[1] not in self.builtins and self.current_token[1] not in self.functions:
            return False
        if self.current_token[1] in ["polygon"]:
            self.location[-1]["latex"] += r"\operatorname{" + self.current_token[1] + r"}\left("  # nopep8
        elif self.current_token[1] in self.functions:
            self.location[-1]["latex"] += self.subscriptify(self.current_token[1]) + r"\left("  # nopep8
        else:
            self.location[-1]["latex"] += "\\" + self.current_token[1] + r"\left("  # nopep8
        builtin = self.current_token[1]
        self.next_token()
        if self.current_token[1] != "(":
            self.raise_error("Expected bracket")
        self.next_token()
        if not self.parse_expression():
            self.raise_error(f"Expected expression after {builtin}")
        while self.current_token[1] != ")":
            if self.current_token[1] != ",":
                self.raise_error("Expected ',' after parameter")
            self.location[-1]["latex"] += ","
            self.next_token()
            if not self.parse_expression():
                self.raise_error(f"Expected expression after {builtin}")
        self.location[-1]["latex"] += r"\right)"
        self.next_token()
        return True

    def parse_comprehension(self):
        if self.current_token[0] != "identifier" and self.tokens[self.position+1][1] != ",":
            return False
        self.location[-1]["latex"] += self.current_token[1]
        self.next_token()
        if self.current_token[1] != "for":
            self.raise_error("Expected 'for'")
        self.location[-1]["latex"] += r"\operatorname{for}"
        self.next_token()
        if self.current_token[0] != "identifier":
            self.raise_error("Expected identifier after 'for'")
        identifier = self.current_token[1]
        self.location[-1]["latex"] += self.current_token[1]
        self.next_token()
        if self.current_token[1] != "=":
            self.raise_error("expected '=' ")
        self.next_token()
        self.location[-1]["latex"] += "="
        if not self.parse_list():
            self.raise_error(f"{identifier} must be a list, not")
        self.next_token()
        return True

    def parse_list(self):
        if self.current_token[1] != "[":
            return False
        self.location[-1]["latex"] += r"\left["
        self.next_token()
        while self.current_token[1] != "]":
            if self.current_token[1] == "]":
                self.location[-1]["latex"] += r"\right]"
                return True
            if self.current_token[1] != ",":
                self.raise_error("expressions must be separated by a ','")
            self.location[-1]["latex"] += ","
            self.next_token()
        self.location[-1]["latex"] += r"\right]"
        self.next_token()
        return True

    def parse_value(self):  # 1232, or x, y or hello
        # check if current token is an identifier or literal
        if self.current_token != None:
            if (self.current_token[0] not in ["identifier", "literal"]) and self.current_token[1] not in ["-", "+"]:
                return False
        else:
            return True
        if self.current_token[1] == "-":
            self.location[-1]["latex"] += "-"
            self.next_token()
        # if it is a literal, decide if it is already defined in the current scope
        if self.current_token[0] == "identifier":
            # define variable
            if self.location[-1]["latex"] == "" and self.tokens[self.position + 1][1] == "=":
                try:
                    self.vars[self.scope] += [self.current_token[1]]
                except KeyError:
                    self.vars[self.scope] = [self.current_token[1]]
            if self.current_token[1] in self.vars.keys() and self.current_token[1] != "global":
                scope = copy.deepcopy(self.current_token[1])
                self.next_token()
                if self.current_token[1] != ".":
                    self.raise_error("expected '.'")
                self.next_token()
                self.scope = scope
                self.parse_value()
                return True
            if self.current_token[1] not in self.vars[self.scope] and self.current_token[1] not in self.constants:
                self.raise_error(f"Variable {self.current_token[1]} not defined")  # nopep8

            self.location[-1]["latex"] += self.subscriptify(
                self.scope + str(self.current_token[1]))
        else:
            self.location[-1]["latex"] += str(self.current_token[1])  # nopep8
        self.next_token()
        return True

    def parse_point(self):
        if self.current_token[1] != "(":
            return False
        self.next_token()
        self.location[-1]["latex"] += r"\left("
        if not self.parse_expression():
            self.raise_error("Points must have two coordinates")
        if self.current_token[1] != ",":
            self.raise_error("Expected ',' in point")
        self.location[-1]["latex"] += self.current_token[1]
        self.next_token()
        if not self.parse_expression():
            self.raise_error("Points must have two coordinates")
        self.location[-1]["latex"] += r"\right)"
        if self.current_token[1] != ")":
            self.raise_error("Expected ')'")
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
    os.system("pause")
