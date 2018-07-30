# Copyright (c) 2018 Serguei Kalentchouk et al. All rights reserved.
# Use of this source code is governed by an MIT license that can be found in the LICENSE file.
from expression_lexer import *

PRECEDENCE = {
    '<': 10, '>': 10, '<=': 10, '>=': 10, '==': 10, '!=': 10,
    '+': 20, '-': 20,
    '*': 30, '/': 30, '%': 30,
}


class Number(object):
    """"""
    def __init__(self, value):
        self.value = value

        if isinstance(value, list):
            if len(value) == 3:
                self.type = 'double3'
            elif len(value) == 4:
                self.type = 'double4'
            else:
                self.type = 'matrix'
            self.value = [float(v) for v in value]
        else:
            self.type = 'double' if '.' in value else 'int'
            self.value = float(value) if self.type == 'double' else int(value)
    
    def negate(self):
        self.value = self.value * -1
    
    def __repr__(self):
        return '(Number: {0}({1}))'.format(self.type, self.value)


class String(object):
    def __init__(self, value, index=None):
        self._value = value
        self.index = index
    
    @property
    def value(self):
        return '{0}{1}'.format(self._value, '[{0}]'.format(self.index) if self.index else '')
    
    def __repr__(self):
        return '(String: {0})'.format(self.value)


class Binary(object):
    def __init__(self, value, left, right):
        self.value = value
        self.left = left
        self.right = right
    
    def __repr__(self):
        return '(Binary: {0} {1} {2})'.format(self.left, self.value, self.right)


class Conditional(object):
    def __init__(self, value, left, right, true, false):
        self.value = value
        self.left = left
        self.right = right
        self.true = true
        self.false = false
    
    def __repr__(self):
        return '(Conditional: {0} {1} {2} ? {3} : {4})'.format(self.left, self.value, self.right, self.true, self.false)


class Function(object):
    def __init__(self, value, args, index=None):
        self.value = value
        self.args = args
        self.index = index
    
    def __repr__(self):
        return '(Function: {0}({1}){2})'.format(self.value, self.args, '[{0}]'.format(self.index) if self.index else '')


class ExpressionParser(object):
    def __init__(self, expression):
        """Initialize expression parser
        
        Args:
            expression (str): Raw math expression to parse
        """
        self._data = ExpressionLexer(expression)

    @property
    def token(self):
        """Get current lexer token
        
        Returns:
            Token: Current token
        """
        return self._data._current

    def parse(self):
        """Parse the entire expression
        
        This is the main executor for the parser.

        Returns:
            Object: Returns the containing AST node
        """
        self._data.next()
        return self.parse_expression()

    def get_precedence(self):
        """Get operator precedence from current token
        
        Returns:
            int: Returns operator prcedence value
        """
        if not self.token or self.token.type is not OperatorToken:
            return -1
        
        return PRECEDENCE[self.token.value]

    def parse_number(self):
        """"Parse current token as number
        
        Returns:
            Number: Returns Number AST node
        """
        num = Number(self.token.value)
        self._data.next()  # consumes number
        
        return num

    def parse_string(self):
        """Parse current token as string

        Returns:
            String: Returns String AST node
        """
        string = String(self.token.value)
        self._data.next() # consumes string

        # if the next token is a square bracket then assuming indexing
        if self.token and self.token.value == '[':
            self._data.next()  # consume open bracket
            if not self.token or self.token.type != NumberToken:
                self._data.error('Expected a numeric index, got "{0}" instead'.format(self.token))
            string.index = self.token.value
            self._data.next() # consume index number
            
            if not self.token or self.token.value != ']':
                self._data.error('Expected a closing bracket, got "{0}"" instead'.format(self.token))
            self._data.next() # consume close bracket

        return string

    def parse_element(self):
        """Parse token element
        
        Returns:
            Object: Returns appropriate AST node
        """
        if not self.token:
            self._data.error('Expected a valid token, got "None" instead')
        
        if self.token.type == NumberToken:
            return self.parse_number()
        elif self.token.type == StringToken:
            # special case for function calls
            next = self._data.peek()
            if next and next.type == BracketToken and next.value == '(':
                return self.parse_function()
            return self.parse_string()
        elif self.token.type == FunctionToken:
            return self.parse_function()
        elif self.token.type == BracketToken and self.token.value == '(':
            return self.parse_parentheses()
        elif self.token.type == OperatorToken and self.token.value == '-':
            # special case for negative values
            self._data.next()  # consume negate
            
            # TODO: complete for other types
            if self.token.type == NumberToken:
                number = self.parse_number()
                number.negate()
                return number
            else:
                self._data.error('Expected a number after negate, got "{0}" instead'.format(self.token.value))
        else:
            self._data.error('Could not handle token "{0}"'.format(self.token))
    
    def parse_expression(self):
        """Parse expression recursively
        
        Returns:
            Object: Returns the containing left most AST node
        """
        left = self.parse_element()
        
        if self.token and self.token.type == OperatorToken:
            left = self.parse_binary_right(0, left)
        
        if self.token and self.token.type == ConditionToken:
            left = self.parse_conditional(left)

        # if self.token:
        #     self.error('Expected end of expression or another operator, got '{0}' instead'.format(self.token))

        return left
    
    def parse_parentheses(self):
        """Parse parentheses
        
        Returns:
            Object: Returns appropriate AST node
        """
        self._data.next()  # consume open paren
        result = self.parse_expression()

        if not result:
            self._data.error('Encountered empty parentheses')

        if not self.token or self.token.value != ')':
            self._data.error('Expected closing parenthesis, got "{0}" instead'.format(self.token))
        
        self._data.next()  # consume closing paren
        return result
    
    def parse_function(self):
        """Parse function expression
        
        Returns:
            Function: Returns Function AST node
        """
        function = self.token.value
        self._data.next()  # consume function
        
        if not self.token or self.token.value != '(':
            self._data.error('Expected function call parentheses, got "{0}" instead'.format(self.token))
        
        args = []
        args_nested = []
        arg_is_list = False
        self._data.next()  # consume open paren
        while True:
            # check if function argument is an array
            if self.token and self.token.value == '[':
                arg_is_list = True
                self._data.next()  # consume open bracket
            
            arg = self.parse_expression()
            if not arg:
                self._data.error('Expected a valid argument, got "None" instead')
            
            if arg_is_list:
                args_nested.append(arg)
            else:
                args.append(arg)
            
            if self.token and self.token.value == ']':
                self._data.next()  # consume close bracket
                
                if self.token and self.token.value in [',', ')']:
                    prev_token = self.token
                    self._data.next()  # consume comma or close paren
                    args.append(args_nested)
                    arg_is_list = False
                    if prev_token.value == ')':
                        break
                else:
                    self._data.error('Expected comma or closing parenthesis, got "{0}" instead'.format(next)) 
            elif self.token and self.token.value == ')':
                self._data.next()  # consume close paren
                break
            elif self.token and self.token.value == ',':
                self._data.next()  # consume comma
            else:
                self._data.error('Expected closing parenthesis, got "{0}" instead'.format(self.token))
        
        # if the next token is a square bracket then we assuming indexing
        index = None
        if self.token and self.token.value == '[':
            self._data.next()  # consume open bracket
            if not self.token or self.token.type != NumberToken:
                self._data.error('Expected a numeric index, got "{0}" instead'.format(self.token))
            index = self.token.value
            self._data.next()  # consume index

            if not self.token or self.token.value != ']':
                self._data.error('Expected a closing bracket, got "{0}" instead'.format(self.token))
            self._data.next()  # consume close bracket

        return Function(function, args, index)

    def parse_binary_right(self, prec, left):
        """Parse binary expression with precendence recursively
        
        Returns:
            Binary: Returns Binary AST node
        """
        while True:
            left_prec = self.get_precedence()
            if left_prec < prec:
                return left
            
            op_value = self.token.value
            self._data.next()  # consume op

            right = self.parse_element()
            if left_prec < self.get_precedence():
                right = self.parse_binary_right(left_prec + 1, right)
            
            left = Binary(op_value, left, right)

    def parse_conditional(self, left):
        """Parse conditional expression

        Returns:
            Condition: Returns Condition AST node
        """
        op_value = self.token.value
        self._data.next()  # consume op

        right = self.parse_expression()
        if not self.token.type == TernaryToken:
            self._data.error('Expected ternary operator, got "{0}" instead'.format(self.token.value))
        
        self._data.next()  # consume op
        true = self.parse_expression()
        false = None
        if self.token.type == TernaryToken:
            self._data.next()  # consume op
            false = self.parse_expression()
        
        return Conditional(op_value, left, right, true, false)