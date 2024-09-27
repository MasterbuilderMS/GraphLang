import sys
import pyperclip
import json


class DesPy:
    def __init__(self, code: str):
        self.code = code
        # line number, only used for more accurate errors
        self.line_nr = 0
        self.token_feed = self.tokens()
        self.returned_token = None
        self.stack = []
        # allowed by desmos
        self.vars = {"x": "x", "y": "y", "X": "X", "Y": "Y"}
        self.precedence = {}
        self.output = {
            "version": 11,
            "randomSeed": "98924066daced716ccd415cdd611bb42",
            "graph": {
                "viewport": {
                    "xmin": -10,
                    "ymin": -18.146718146718147,
                    "xmax": 10,
                    "ymax": 18.146718146718147
                }
            },
            "expressions": {
                "list": [

                ]


            },
            "includeFunctionParametersInRandomSeed": "true",

        }
        self.expression_id = 0

    def raise_error(self, message: str):
        raise ValueError(message)

    # lexer
    def tokens(self):
        for line in self.code.split("\n"):
            self.line_nr += 1
            for token in line.split(" "):
                if token in ["+", "*", "/", "-", "="]:
                    yield ("operator", token)
                elif token in ["ns", "fn", "macro", "if", "for"]:
                    yield ("keyword", token)
                elif token.isnumeric():
                    yield ("number", token)
                elif token.isalpha():
                    yield ("identifier", token)
                elif token == " ":
                    pass
                else:
                    self.raise_error("Unknown token")
            yield ("\n",)

    def next_token(self):
        if self.returned_token:
            token = self.returned_token
            self.returned_token = None
        else:
            try:
                token = next(self.token_feed)
            except StopIteration:
                token = None
        return token

    def return_token(self, token):
        if self.returned_token is not None:
            raise RuntimeError("Cannot return more that one token at once")
        self.returned_token = token

    def stack_pop(self):
        return self.stack.pop()

    def stack_push(self, token):
        return self.stack.append(token)

    def subscriptifise(self, text):
        if len(text) > 1:
            text = text[0] + "_{" + text[1:] + "}"

        return text

    def run(self):

        try:
            return self.parse_program()
        except ValueError as exc:
            print(str(exc))
            return False

    # =====Parser===
    # below are methods that parse each token
    # we are effectively checking that it conforms with the grammar

    def parse_program(self):
        # check if their is a statement at the start
        if not self.parse_statement():
            self.raise_error("Expected: statement")
        token = self.next_token()
        # repeat until end of program
        while token is not None:
            self.return_token(token)
            # if there is a statement
            if not self.parse_statement():
                self.raise_error("Expected: statement")
            token = self.next_token()

        # copy output json to clipboard
        self.output
        data = json.dumps(self.output)
        pyperclip.copy(data)
        print("Copied: ", data)

    def parse_statement(self):
        if not self.parse_expression_statement():
            self.raise_error("Expected statement")
        token = self.next_token()
        if token[0] != "\n":
            self.raise_error("Expected: end of line")
        return True

    def parse_number(self):
        token = self.next_token()
        if token[0] not in ["number", "identifier"]:
            self.return_token(token)
            return False

        if token[0] == "identifier":
            if (token[1] not in self.vars.keys()) and (token[1] not in ["x", "y", "X", "Y"]):
                self.raise_error(
                    f"Syntax Error: Unknown variable {token[1]}")
            else:
                self.stack_push(self.vars[token[1]])
        else:
            self.stack_push(token[1])
        return True

    def parse_expression_statement(self):
        expression = {}  # expression as desmos json
        token = self.next_token()
        identifier = None
        operator = None
        value = None
        self.output["expressions"]["list"].append(
            {"type": "expression", "id": self.expression_id, "color": "#c74440", "latex": None})

        if token[0] != "identifier":
            self.return_token(token)
            return False

        identifier = token[1]
        self.expression_id += 1
        token = self.next_token()
        if token[0] != "operator":
            self.raise_error("Expected: operator")

        identifier = self.subscriptifise(identifier)

        operator = token[1]
        if not self.parse_number():
            self.raise_error("Expected: expression")
        self.vars[identifier] = self.stack_pop()
        value = str(self.vars[identifier])
        self.output["expressions"]["list"][next((index for (index, d) in enumerate(
            self.output["expressions"]["list"]) if d["id"] == self.expression_id-1), None)]["latex"] = identifier + operator + value
        return True


if __name__ == "__main__":
    with open(sys.argv[1], "rt") as f:
        # with open(r".\src\parser\main.despy", "rt") as f:
        code = f.read()
        program = DesPy(code)
        program.run()
