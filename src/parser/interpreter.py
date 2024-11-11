'''
Interpreter for the Graphlang programming language

'''
#!/usr/bin/env python3
import pprint
import re
import json
import sys
import time
import os
import copy
from Utils import colors
import pyperclip


class Error(BaseException):
    """Class for Graphlang Errors

    Arguments:
        BaseException -- _description_
    """

    def __init__(self, message: str, lines: list, line_nr: int):
        """
        Raise an error with the given message, including the line number and code above it

        Arguments:
            message -- _description_
            lines -- _description_
            line_nr -- _description_
        """
        self.message = "Syntax Error: " + message
        self.line_number = line_nr
        self.new_message = f'''
Traceback (most recent call last):
File {colors.BLUE}"<{sys.argv[1]}>"{colors.END}, line {colors.BLUE}{self.line_number}{colors.END}, in {colors.BLUE}<module>{colors.END}:
    {lines[self.line_number - 1]}
    ^'''
        for _ in range(len(lines[self.line_number-1])):
            self.new_message += "^"
        self.new_message += f"\nSyntax Error: {
            colors.RED}{message}{colors.END}"
        super().__init__(self.new_message)


class GraphLangInterpreter:
    """Class for the Graphlang interpreter (duh)
        Not really sure what else to write in this docstring :(
    """

    def __init__(self, code, debug=False):
        self.debug = debug
        self.code: str = code
        self.tokens: list = []
        self.vars: dict[list] = {
            'hsv': None,
            'rgb': None,
            'sin': None,
            'cos': None,
            'tan': None,
            'csc': None,
            'sec': None,
            'cot': None,
            'arcsin': None,
            'arcos': None,
            'arctangent': None,
            'arccosecant': None,
            'arcsecant': None,
            'arccotangent': None,
            'mean': None,
            'median': None,
            'min': None,
            'max': None,
            'quartile': None,
            'quantile': None,
            'stdev': None,
            'stdevp': None,
            'varp': None,
            'mad': None,
            'cov': None,
            'covp': None,
            'corr': None,
            'spearman': None,
            'stats': None,
            'count': None,
            'total': None,
            'join': None,
            'sort': None,
            'shuffle': None,
            'unique': None,
            'histogram': None,
            'dotplot': None,
            'boxplot': None,
            'random': None,
            'exp': None,
            'ln': None,
            'log': None,
            'int': None,
            'sum': None,
            'prod': None,
            'tone': None,
            'lcm': None,
            'sqrt': None,
            'polygon': None,
            "X": None,
            "Y": None,
            "x": None,
            "y": None
        }
        self.line_nr: int = 0
        self.output: dict = {}
        self.expression_id: int = 0
        self.folder_id: int = 0
        self.token_patterns: list[tuple[str, str]] = [
            ("keyword", r"\b(fn|ns|if|for|macro|import)\b"),
            ("identifier", r"[A-Za-z_][A-Za-z0-9_]*"),
            ("literal", r"\d+"),
            ("punctuation", r"[\{\}\[\]\(\)\.\,\;\!]"),
            ("operator", r"->|\+|-|\*|/|>|<|>=|<=|!=|=|\^"),
            ("skip", r"[ \t]+"),
            ("note", r"\".*?\"|'.*?'"),
            ("comment", r"#.*"),
            ("line", r"\n")
        ]
        self.position = 0
        self.tokens = self.lex(self.code)
        self.position = 0
        self.lines = self.code.splitlines()
        try:
            self.current_token: tuple = self.tokens[0]
        except IndexError:
            self.current_token = None

        self.expression_template = None
        self.note_template = None
        self.folder_template = None
        self.location = 0
        self.tokens.append(("line", "\n"))  # append an item to fix parsing
        self.builtins = ["hsv", "rgb",  # colors
                         "sin", "cos", "tan",  # trigonometry
                         "csc", "sec", "cot",  # 1/trig
                         "arcsin", "arcos", "arctangent",  # trig^-1
                         "arccosecant", "arcsecant", "arccotangent",  # 1/trig^-1
                         "mean", "median",  # averages
                         "min", "max", "quartile", "quantile",  # stuff
                         "stdev", "stdevp", "varp",  # Literally no clue what these do
                         "mad", "cov", "covp", "corr",  # same here
                         "spearman", "stats", "count", "total",  # same here
                         "join", "sort", "shuffle", "unique",  # list operations
                         "histogram", "dotplot", "boxplot",  # plots
                         "random",  # duh
                         "exp", "ln", "log", "int",  # exponential
                         "sum", "prod",  # sum and product
                         "tone",  # tone
                         "lcm", "sqrt", "polygon"]  # random stuff
        self.functions = []
        self.macros: list[dict[str:str, str:str]] = []  # user-defined macros
        self.special = {"__name__": ""}  # special variables
        self.scope_path = []
    # lexer

    def lex(self, code):
        """
        Lexes the code and adds tokens to self.tokens.

        Returns
        -------
        Tokens
        """
        starting_position = copy.deepcopy(self.position)
        self.position = 0
        tokens = []
        token_regex = '|'.join(
            f'(?P<{pair[0]}>{pair[1]})' for pair in self.token_patterns)
        matcher = re.compile(token_regex).match(code)
        while matcher is not None:
            token_type = matcher.lastgroup
            value = matcher.group(token_type)
            if token_type == "literal":
                value = int(value)
                tokens.append((token_type, value))
            elif token_type in ["skip", "comment"]:
                pass
            else:
                tokens.append((token_type, value))
            self.position = matcher.end()
            matcher = re.compile(token_regex).match(code, self.position)
        try:
            if self.position != len(code):
                self.raise_error(
                    f"Unknown character: {code[self.position]} at {self.line_nr}: {self.position}"  # nopep8
                )  # nopep8
        except AttributeError:
            pass
        self.position = starting_position
        return tokens

    # ======= Utility functions =======
    # functions that are used to navigate the token list,
    # control the stack, and raise errors

    def run(self):
        """Run the interpreter, lexing, parsing, evaluating, and copying output to the clipboard."""
        # setup exception handling hook

        def custom_excepthook(exc_type, exc_value, exc_traceback):
            if isinstance(exc_value, Error):
                print(f"{exc_value}")
                if self.debug:
                    print(f'{colors.PURPLE} Debug Info: {colors.END}')
                    pprint.pprint(self.vars)  # nopep8{self.vars}

                os.system("pause")
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
            print(self.macros)

    def raise_error(self, message):
        """
        Raise an error with the given message, including the line number and code above it

        :param message: The error message to be displayed
        :type message: str
        """
        raise Error(message, self.lines, self.line_nr)

    # get the next token

    def next_token(self):
        """
        Get the next token from the token list, 
        incrementing the line number if the current token is a newline.
        If the end of the list is reached, set the current token to None.
        """
        try:
            if self.current_token[0] == "line":
                self.line_nr += 1
            self.current_token = self.tokens[self.position + 1]
            self.position += 1
            # print(self.current_token)
        except IndexError:
            self.current_token = None

    def previous_token(self):
        """
        Get the next token from the token list, 
        incrementing the line number if the current token is a newline.
        If the end of the list is reached, set the current token to None.
        """
        try:
            if self.current_token[0] == "line":
                self.line_nr -= 1
            self.current_token = self.tokens[self.position - 1]
            self.position -= 1
            # print(self.current_token)
        except IndexError:
            self.current_token = None

    def peek_token(self, num):
        """looks ahead at the next token

        Arguments:
            num -- amount to look ahead

        Returns:
            token
        """
        try:
            return self.tokens[self.position + num]
        except IndexError:
            return None

    def subscriptify(self, text):
        """
        This function converts the given text into a subscript format 
        if the text length is greater than 1.

        Parameters:
            text (str): The input text to be converted into subscript format.

        Returns:
            str: The text converted into subscript format.
        """
        if len(list(text)) == 1:
            return text
        return f"{text[0]}_{{{text[1:]}}}"

    def get_variables(self, scope_path):
        # scope path is a list of scope to get to the variable we want
        """
        Retrieves a variable from the given scope path.

        Parameters:
            scope_path (list): The list of scopes to get to the variable.

        Returns:
            dict: The variable's dictionary.
        """

        variables = copy.deepcopy(self.vars)
        for scope in scope_path:
            variables = copy.deepcopy(variables[scope])
        return variables

    def set_variables(self, scope_path):
        # scope path is a list of scope to get to the variable we want
        """
        Retrieves a variable from the given scope path and can edit it

        Parameters:
            scope_path (list): The list of scopes to get to the variable.

        Returns:
            dict: The variable's dictionary.
        """

        variables = self.vars
        for scope in scope_path:
            variables = variables[scope]
        return variables

    def add_variable(self, scope_path, name, value):
        """
        Adds a variable to the given scope path.

        :param scope_path: The list of scopes to get to the variable.
        :type scope_path: list
        :param name: The name of the variable.
        :type name: str
        :param value: The value of the variable.
        :type value: Any
        """

        current_scope = self.vars
        for scope in scope_path:
            if scope not in current_scope:
                current_scope[scope] = {}
            current_scope = current_scope[scope]

        current_scope[name] = value

    def check_variable(self, scope_path: str, name):
        """
        Checks if a variable exists in the given scope path.
        If it
        If the variable name is unqualified (i.e. not dot notation), 
            it checks if the variable exists in the current scope.
        If the variable name is qualified (i.e. it has dot notation), 
            it checks if the variable exists in the resolved scope.

        Parameters:
            scope_path (str): The scope path to check the variable in.
            name (str): The name of the variable to check.

        Returns:
            bool: True if the variable exists, False if it does not.
        """
        if name in self.vars:
            if self.tokens[self.position+1][1] == ".":
                self.scope_path.append(name)
            return True

        checking = []
        current_scope = self.vars
        for scope in scope_path:
            if scope not in current_scope:
                return False
            current_scope = current_scope[scope]
            checking.append(name in current_scope)
        return any(checking)

    def open_import(self, path, module_name):
        with open(path, "r", encoding="utf-8") as module:
            self.next_token()  # skip import
            self.next_token()  # skip name
            self.next_token()  # move onto next token
            imported = module.read()
            tokens_to_insert = [
                ("keyword", "ns"),
                ("identifier", module_name),
                ("punctuation", "{"),
                ("line", "\n")
            ] + self.lex(imported) + [
                ("line", "\n"),
                ("punctuation", "}")
            ]

            # Reverse the list for the insertion order
            tokens_to_insert = list(reversed(tokens_to_insert))

# Insert each token at the specified position
            for token in tokens_to_insert:
                self.tokens.insert(self.position + 1, token)

            self.code = ' '.join([str(token[1]) for token in self.tokens])
            self.lines = self.code.splitlines()
    # ====== Parsing statements ========
    # functions for checking that each token conforms with the grammar
    # each function returns true or false

    def parse_program(self):
        """
        parse_program is the top-level parsing function. It parses a complete program
        into a JSON object that is compatible with Graphing Calculator's data format.

        The function works by parsing a statement, and then keeping track of the
        current token. If the current token is not a newline token, it will parse
        another statement. If the current token is a newline token, it will ignore
        it and move on to the next token. This is done until the current token is
        None.

        At the start of the function, the output dictionary is initialized with
        the required fields for Graphing Calculator.

        :return: None
        """
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
        """
        parse_statement parses a single statement in the language. 
        It first skips through lines and then adds a new expression to the output. 
        If the current token is a namespace, function, expression, or note, it parses that. 
        If none of those, it raises an error. 
        It then moves the position to the next token and returns True.

        Returns:
            bool: True if the statement was parsed successfully, False otherwise.
        """
        if self.current_token is None:  # if there is no statement, return true
            return True
        while self.current_token[0] == "line":
            if self.tokens[self.position + 1] is None:
                return True
            # skip through extra lines
            self.next_token()
        self.location: list = self.output["expressions"]["list"]
        self.location.append(copy.deepcopy(self.expression_template))
        self.expression_id += 1
        self.location[-1]["id"] = self.expression_id
        self.location[-1]["folderId"] = self.folder_id
        if not self.parse_namespace() and not self.parse_function() and not self.parse_expression() and not self.parse_note() and not self.parse_macro() and not self.parse_import():
            self.raise_error("Expected statement")
        self.next_token()
        return True

    def parse_import(self):
        """Parses an import statement - copies tokens into list

        Returns:
            true if successful import
    """
        if self.current_token[1] != "import":
            return False
        self.next_token()
        module_name = copy.deepcopy(self.current_token[1])
        imported = ""
        stdlib_path = os.path.join(os.path.dirname(
            __file__), "..", "stdlib", self.current_token[1] + ".graphlang")
        try:
            self.open_import(
                ".\\" + self.current_token[1] + ".graphlang", module_name=module_name)
        except FileNotFoundError:
            try:
                self.open_import(stdlib_path,
                                 module_name=module_name)
            except FileNotFoundError:
                print("file not found")
        return True

    def parse_note(self):
        """
        This function parses a note definition in the language and adds the note text to the output.

        It first checks if the current token is "note". If not, it returns False.

        Then it adds the note text to the current expression.

        Returns True if the note was parsed successfully, False otherwise.
        """
        if self.current_token[0] != "note":
            return False
        self.location.append(copy.deepcopy(self.note_template))
        self.location[-1]["text"] += str(self.current_token[1])
        self.next_token()
        return True

    def parse_namespace(self):
        """
        This function parses a namespace definition in the language and adds the folder to the output.

        It first checks if the current token is "ns". If not, it returns False.

        Then it adds the namespace name to the current expression and checks if the next token is an identifier.
        If not, it raises an error.

        Then it adds the folder to the output and changes the folder id to the current expression id.
        It then parses all the statements inside the namespace.

        Finally, it resets the folder id back to 0 and the scope back to "global".

        Returns True if the namespace was parsed successfully, False otherwise.
        """
        if self.current_token[1] != "ns":
            return False
        self.location[-1] = copy.deepcopy(self.folder_template)
        self.location[-1]["id"] = self.expression_id
        self.next_token()
        if self.current_token[0] != "identifier":
            self.raise_error("Expected identifier")
        # check if a scope already exists
        try:
            if self.current_token[1] in list(self.get_variables(self.scope_path).keys()):
                self.set_variables(
                    self.scope_path[:-1])[self.current_token[1]] = {}
        except KeyError:
            self.get_variables(
                self.scope_path[:-1])[self.current_token[1]] = {}

        # add folder to self.vars

        # self.add_variable(self.scope_path, self.current_token[1], {})
        self.scope_path.append(self.current_token[1])
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
                while self.current_token[0] in ["line", "comment"]:
                    self.next_token()
        except TypeError:
            pass
        self.scope_path.pop()
        self.next_token()
        return True

    def parse_function(self):
        """
        parse_function parses a function definition in the language and adds the function to the output.

        It first checks if the current token is "fn". If not, it returns False.

        Then it adds the function name and parameters to the current expression.

        Then it parses all the statements inside the function.

        Finally, it resets the scope back to "global" and returns True.

        Returns True if the function was parsed successfully, False otherwise.

        """

        if self.current_token[1] != "fn":
            return False
        self.next_token()
        if self.current_token[0] != "identifier":
            self.raise_error("Expected function name after defintion")
        self.location[-1]["latex"] += self.subscriptify(self.current_token[1])
        self.location[-1]["latex"] += r"\left("
        self.add_variable(self.scope_path, self.current_token[1], {})
        self.scope_path.append(self.current_token[1])
        self.functions.append(self.current_token[1])
        self.next_token()
        if self.current_token[1] != "(":
            self.raise_error("Expected (")
        self.next_token()
        while self.current_token[1] != ")":
            if self.current_token[0] != "identifier":
                self.raise_error("Expected parameter")
            self.location[-1]["latex"] += self.subscriptify(self.scope_path[-1] + self.current_token[1])  # nopep8
            self.add_variable(self.scope_path, self.current_token[1], None)
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
        self.scope_path.pop()
        return True

    def parse_expression(self):  # x + 1
        """
        parse_expression parses an expression from the source code. 
        It first attempts to parse a point, and if that fails, 
        it attempts to parse a function call, a value, a list, or a point. 
        If any of those fail, it raises an error. 
        After parsing the first part of the expression, 
        it checks to see if there is an operator, 
        and if there is, it parses the rest of the expression. 
        It keeps track of the current position and the current latex string 
        so that if a parse fails, it can go back to the position 
        right before the parse started and try a different parse. ]
        t also keeps track of the current scope and the current folder id.

        Returns:
            bool: True if the expression was parsed successfully, False otherwise.
        """

        # check if it is a point first:
        # safety in case it isn't a point so we can jump back here
        return_latex = copy.deepcopy(self.location[-1]["latex"])
        return_location = copy.deepcopy(self.position)
        try:
            if not self.parse_point():
                self.position = return_location - 1
                self.location[-1]["latex"] = return_latex
            else:
                if self.parse_operator():
                    self.parse_expression()
                if self.current_token is not None:
                    if self.current_token[0] == "line" or self.current_token[1] in [",", "]", ")"]:
                        return True
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
            if self.parse_operator():
                self.parse_expression()

        else:
            if not self.parse_function_call() and not self.parse_macro_call() and not self.parse_value() and not self.parse_list() and not self.parse_point() and not self.parse_comprehension():
                return False
            if self.parse_operator():
                self.parse_expression()

        if self.current_token is not None:
            # tokens that can end an expression
            if self.current_token[0] == "line" or self.current_token[1] in [",", "]", ")", "}"]:
                return True
        else:
            return True

    def parse_macro(self):
        """
        parse_macro parses a macro definition from the source code. It first checks if the current token is "macro". If not, it returns False.

        It then adds the macro name to the current expression and checks if the next token is an identifier.
        If not, it raises an error.

        Then it adds the macro to the list of macros and adds the macro name to the current scope.
        It then parses the parameters of the macro by checking if the current token is an identifier.
        If not, it raises an error.

        Then it parses the latex string of the macro by checking if the current token is not "}".
        If it is, it raises an error.

        Finally, it pops the current scope and returns True.

        Returns:
            bool: True if the macro was parsed successfully, False otherwise.
        """
        if self.current_token[1] != "macro":
            return False
        self.next_token()
        macro_name = self.current_token[1]
        if self.current_token[0] != "identifier":
            self.raise_error("Expected identifier after macro")
        self.macros.append({"name": macro_name, "latex": "", "args": []})  # nopep8
        self.add_variable(self.scope_path, self.current_token[1], {})
        self.scope_path.append(self.current_token[1])
        self.next_token()
        if self.current_token[1] != "!":
            self.raise_error("Macro names must end in !")
        self.next_token()
        if self.current_token[1] != "(":
            self.raise_error("Expected (")
        self.next_token()
        while self.current_token[1] != ")":
            if self.current_token[0] != "identifier" and self.current_token[1] not in ["__name__"]:
                self.raise_error("Expected parameter")
            self.add_variable(self.scope_path, self.current_token[1], {})
            self.macros[-1]["args"].append(self.current_token[1])
            self.next_token()
            if self.current_token[1] == ")":
                self.next_token()
                break
            if self.current_token[1] != ",":
                self.raise_error("Expected ',' between parameters")
            self.macros[-1]["latex"] += ","
            self.next_token()
        if self.current_token[1] != "{":
            self.raise_error("Expected { after function definition")
        self.next_token()
        brackets = 0
        while self.current_token[1] != "}" or brackets != 0:
            if self.current_token[1] == "{":
                brackets += 1
            elif self.current_token[1] == "}":
                brackets -= 1
            self.macros[-1]["latex"] += str(self.current_token[1])
            self.next_token()
        self.macros[-1]["latex"] = self.macros[-1]["latex"][1:]
        self.scope_path.pop()
        return True

    def parse_comprehension(self):
        """Parses a list comprehension 
        [2i for i=[1,2,3,4,5]]

        """
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
        """Parses a list
        e.g. [1,2,3,4]
        Returns:
            _description_
        """
        if self.current_token[1] != "[":
            return False
        self.location[-1]["latex"] += r"\left["
        self.next_token()
        while self.current_token[1] != "]":
            self.parse_expression()
            if self.current_token[1] == "]":
                break
            if self.current_token[1] != ",":
                self.raise_error("expressions must be separated by a ','")
            self.location[-1]["latex"] += ","
            self.next_token()
        self.location[-1]["latex"] += r"\right]"
        self.next_token()
        return True

    def parse_value(self):  # 1232, or x, y or hello
        # check if current token is an identifier or literal
        """
        Parses a value from the source code, which can be an identifier, literal, or unary operation.

        The function first checks if the current token is an identifier, literal, or a unary operator
        such as '-' or '+'. If the token is a unary operator, it adjusts the current latex string
        accordingly.

        If the token is an identifier, it attempts to define it as a variable if it is followed by
        an '=' sign, while also storing it in the current scope. It checks if the variable already
        exists in the scope and raises an error if it is not defined. If the identifier is part of
        a member access (indicated by a '.' token), it parses the expression further.

        For literals, it converts them to a string and appends it to the latex representation.

        Finally, it processes any list access and returns True if the value is parsed successfully.

        Returns:
            bool: True if the value is parsed successfully, False otherwise.
        """
        if self.current_token is not None:
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
                    self.add_variable(
                        self.scope_path, self.current_token[1], None)
                    self.special["__name__"] = self.current_token[1]
                    print(self.special)
                except KeyError:
                    self.add_variable(
                        self.scope_path, self.current_token[1], None)
                    self.special["__name__"] = self.current_token[1]
                    print(self.special)
            path = copy.deepcopy(self.scope_path)
            path.append(self.current_token[1])
            # check if variable exists
            if not self.check_variable(self.scope_path, self.current_token[1]):
                self.raise_error(f"Variable {self.current_token[1]} not defined")  # nopep8
            if self.tokens[self.position + 1][1] == ".":
                self.next_token()
                self.next_token()
                self.parse_expression()
                self.scope_path.pop()

            else:
                try:
                    self.location[-1]["latex"] += self.subscriptify(
                        self.scope_path[-1] + str(self.current_token[1]))
                except IndexError:
                    self.location[-1]["latex"] += self.subscriptify(
                        self.current_token[1])

        else:
            self.location[-1]["latex"] += str(self.current_token[1])  # nopep8
        self.next_token()
        self.parse_list_access()
        return True

    def parse_list_access(self):
        """
        Parses list access in the source code.

        Checks if the current token indicates the start of a list access ('[').
        If so, it proceeds to parse the list. If not, it returns False.

        Returns:
            bool: False if the current token is not '[', indicating no list access.
        """

        if self.current_token[1] == "[":
            self.parse_list()
        else:
            return False

    def parse_function_call(self):
        """
        Parses a function call in the source code.

        Checks if the current token indicates the start of a function call (an identifier or a built-in function).
        If so, it proceeds to parse the function call. If not, it returns False.

        Returns:
            bool: False if the current token is not an identifier or a built-in function, indicating no function call.
        """
        if self.current_token[1] not in self.functions and self.current_token[1] not in self.builtins:
            return False
        if self.current_token[1] in ["polygon", "rgb", "hsv"]:
            self.location[-1]["latex"] += "\\operatorname{" + self.current_token[1] + "}" + "\\left("  # nopep8
        elif self.current_token[1] in self.functions:
            self.location[-1]["latex"] += self.subscriptify(self.current_token[1]) + "\\left("  # nopep8
        else:
            self.location[-1]["latex"] += "\\" + self.current_token[1] + "\\left("  # nopep8
        function = self.current_token[1]
        self.next_token()
        if self.current_token[1] != "(":
            self.raise_error("Expected '('")
        self.next_token()
        if not self.parse_expression():
            self.raise_error("Expected expression")
        while self.current_token[1] != ")":
            if self.current_token[1] != ",":
                self.raise_error("Expected ',' after parameter")
            self.location[-1]["latex"] += ","
            self.next_token()
            if not self.parse_expression():
                self.raise_error(f"Expected expression after {function}")
        self.location[-1]["latex"] += "\\right)"
        self.next_token()
        return True

    def parse_macro_call(self):
        """
        Parses a macro call (e.g. Rectangle!())
        Automatically injects the tokens from the macro into the token list
        :returns False: if macro is parsed incorrectly, or it just isn't  macro
        :rtype: bool
        :returns True: successful macro passing
        :raises SyntaxError: if macro is not defined       
        """
        if self.tokens[self.position + 1][1] != "!":
            return False

        if self.current_token[1] in [i["name"] for i in self.macros]:
            macro = next((item for item in self.macros if item['name'] == self.current_token[1]), None)  # nopep8
            self.next_token()
            if self.current_token[1] != "!":
                self.raise_error("Expected ! after macro name")
            self.next_token()
            if self.current_token[1] != "(":
                self.raise_error("Expected ( after macro name")
            self.next_token()
            macro_text = macro["latex"]

            for arg in macro["args"]:
                if arg in ["__name__"]:
                    if self.special[arg] == "":
                        self.special[arg] = "" + macro["name"] + "Object"

                    self.previous_token()
                    self.previous_token()
                    self.tokens.pop(self.position)
                    self.tokens.pop(self.position)
                    self
                    macro_text = macro["latex"].replace("{" + arg + "}", " " + copy.deepcopy(self.special[arg]))  # nopep8
                    continue
                if self.current_token[1] != ")":
                    macro_text = macro["latex"].replace("{" + arg + "}", self.current_token[1])  # nopep8

            # update lines, code and token list
            self.next_token()
            self.tokens.insert(self.position + 1, ("line", "\n"))
            for token in reversed(self.lex(macro_text)):
                self.tokens.insert(self.position + 1, token)
            self.tokens.insert(self.position + 1, ("line", "\n"))

            self.code = ' '.join([str(token[1]) for token in self.tokens])
            self.lines = self.code.splitlines()
            return True
        else:
            self.raise_error("Macro not defined")

    def parse_point(self):
        """parses a point

        Returns:
            ...
        """
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
        """Parses an operator

        Returns:
            True if parsed successfully, ... 
            False (i am sure you can figure out when false is returned )
        """
        if self.current_token is not None:
            if self.current_token[1] not in ["^", "=", "->", "-", "+", "/", "*", "<", ">", "<=", ">="]:
                return False
        else:
            return False
        if self.current_token[1] == "->":
            self.location[-1]["latex"] += "\\to "
        else:
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
        sys.argv.append(input("Input file path: "))
        exit()
    time.sleep(0.05)
    try:
        with open(sys.argv[1], "rt", encoding="utf-8") as f:
            text_code = f.read()
            os.system("cls")
            for i in range(10):
                os.system("cls")
                print(colors.GREEN + "Compiling" + ("............."*i) + colors.END)  # nopep8
                time.sleep(0.001)

            _ = GraphLangInterpreter(text_code, debug=True)
            _.run()
    except FileNotFoundError:
        print(colors.RED +
              '''Failed to start compilation. Are you sure the file exists?'''
              + colors.END
              )
        sys.exit()
