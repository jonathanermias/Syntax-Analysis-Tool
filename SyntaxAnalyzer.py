# Jonathan Ermias
import ast
import re
import keyword
import builtins

class CodeAnalyzer(ast.NodeVisitor):
    def __init__(self):
        """initialize the analyzer to collect issues, track variables, and define scopes.
        this class traverses the abstract syntax tree of python code to detect various
        coding issues such as naming conventions, unused variables, and potential logical errors.
        it maintains scopes to accurately track variable definitions and usages.
        """
        super().__init__()
        self.issues = []               # list to store detected issues
        self.assignments = {}          # track variable assignments with line numbers
        self.usages = {}               # track variable usages with line numbers
        self.loop_depth = 0            # counter for loop nesting depth
        self.scopes = [{}]             # stack of variable scopes (starting with global scope)
        self.current_function = None   # name of the function currently being analyzed
        self.functions = {}            # store function information like returns and line numbers
        self.imports = set()           # set of imported module names
        self.used_imports = set()      # set of imports that are actually used
        self.class_names = set()       # set of defined class names
        self.global_scope = {}         # dictionary representing the global scope
        self.current_scope = self.global_scope  # the current scope being analyzed
        self.global_vars = set()       # set of variables declared as global
        self.nonlocal_vars = set()     # set of variables declared as nonlocal

        # collect built-in function names and keywords to avoid false positives
        self.built_in_names = set(dir(builtins)).union(set(keyword.kwlist))
        # optionally, include methods of basic built-in types to the set
        type_methods = []
        for typ in (str, list, dict, tuple, set):
            # add methods of each type, excluding special methods (__methods__)
            type_methods.extend([method for method in dir(typ) if not method.startswith('__')])
        self.built_in_names.update(type_methods)
        self.module_level_assignments = {} # For checking constant naming

    def _add_issue(self, code, message, line, col=0):
        """Helper to add issues with PEP 8 code if applicable."""
        self.issues.append(f"{code}: {message} (line {line})")

    def generic_visit(self, node):
        """override generic_visit to set parent references for nodes.
        this helps in navigating the ast when parent nodes are needed.
        """
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.AST): # Ensure child is an AST node
                child.parent = node               # set the parent attribute
        super().generic_visit(node)           # continue the generic visit

    def visit_Module(self, node):
        """visit the module node to start analysis and check for unused imports after traversal."""
        self.current_scope = self.global_scope  # set the current scope to global
        
        # Check for module-level constant naming after all assignments are processed
        # This is a heuristic: if assigned at module level and all upper, it's a constant.
        # If reassigned later, it's not a constant. This basic check won't catch reassignments.
        for child_node in node.body:
            if isinstance(child_node, ast.Assign):
                for target in child_node.targets:
                    if isinstance(target, ast.Name):
                        self.module_level_assignments[target.id] = target.lineno
                        # Heuristic for constants: if all caps, assume it's a constant
                        # A more robust check would verify it's not reassigned.
                        if not re.match(r'^[A-Z_][A-Z0-9_]*$', target.id) and target.id.isupper():
                            self._add_issue("C0103", f"Constant '{target.id}' should be in UPPER_CASE_WITH_UNDERSCORES", target.lineno)


        self.generic_visit(node)                # recursively visit all child nodes
        unused_imports = self.imports - self.used_imports  # determine unused imports
        for imp_name, imp_lineno in self.imports: # Store imports as (name, lineno)
            if imp_name not in self.used_imports:
                 self._add_issue("W0611", f"Unused import '{imp_name}'", imp_lineno)


    def visit_Import(self, node):
        """record imported module names and add them to the current scope. Check E401."""
        if len(node.names) > 1:
            self._add_issue("E401", "Multiple imports on one line", node.lineno)
        for alias in node.names:
            import_name = alias.asname or alias.name  # use alias if present
            self.imports.add((import_name, node.lineno)) # Store with line number
            self.current_scope[import_name] = 'import'  # mark as imported in current scope
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """record names imported from a module and add them to the current scope. Check E401."""
        # E401 for 'from foo import a, b' is generally accepted by linters like Flake8,
        # but pycodestyle might flag it if it's too long.
        # For simplicity, we won't flag E401 here unless it's multiple 'from x import y; from a import b'
        # which AST parses as separate ImportFrom nodes.
        for alias in node.names:
            import_name = alias.asname or alias.name
            self.imports.add((import_name, node.lineno))
            self.current_scope[import_name] = 'import'
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """check class naming conventions and create a new scope for the class."""
        self.current_scope[node.name] = 'class'  # add class name to current scope
        self.class_names.add(node.name)          # add to set of class names
        if not re.match(r'^[A-Z][a-zA-Z0-9]*$', node.name):
            # report naming violation if not in camelcase
            self._add_issue("C0103", f"Class '{node.name}' should be in CapWords (CamelCase) format", node.lineno)
        self.scopes.append({})                   # create a new scope for the class
        prev_scope = self.current_scope          # save current scope
        self.current_scope = self.scopes[-1]     # set current scope to class scope
        self.generic_visit(node)                 # visit child nodes within the class
        self.scopes.pop()                        # restore the previous scope
        self.current_scope = prev_scope

    def visit_FunctionDef(self, node):
        """check function naming conventions, docstrings, and prepare for return analysis.
        this function also creates a new scope for the function and adds its parameters to the scope.
        after visiting the function body, it checks for inconsistent return statements.
        """
        if not (node.name.startswith('__') and node.name.endswith('__')):
            # check if function name is in snake_case
            if not re.match(r'^[a-z_][a-z0-9_]*$', node.name):
                self._add_issue("C0103", f"Function '{node.name}' should be in snake_case", node.lineno)
        if not ast.get_docstring(node):
            # report missing docstring
            self._add_issue("C0111", f"Function '{node.name}' is missing a docstring", node.lineno)
        
        # Check argument names
        for arg in node.args.args:
            if not re.match(r'^[a-z_][a-z0-9_]*$', arg.arg) and arg.arg != 'self' and arg.arg != 'cls':
                 self._add_issue("C0103", f"Argument '{arg.arg}' in function '{node.name}' should be in snake_case", arg.lineno)
        if node.args.vararg:
            if not re.match(r'^[a-z_][a-z0-9_]*$', node.args.vararg.arg):
                 self._add_issue("C0103", f"Variable argument '*{node.args.vararg.arg}' in function '{node.name}' should be in snake_case", node.args.vararg.lineno)
        if node.args.kwarg:
            if not re.match(r'^[a-z_][a-z0-9_]*$', node.args.kwarg.arg):
                 self._add_issue("C0103", f"Keyword argument '**{node.args.kwarg.arg}' in function '{node.name}' should be in snake_case", node.args.kwarg.lineno)
        for arg in node.args.kwonlyargs:
            if not re.match(r'^[a-z_][a-z0-9_]*$', arg.arg):
                 self._add_issue("C0103", f"Keyword-only argument '{arg.arg}' in function '{node.name}' should be in snake_case", arg.lineno)

        for arg_default in node.args.defaults:
            # check for mutable default arguments
            if isinstance(arg_default, (ast.List, ast.Dict, ast.Set)):
                self._add_issue("W0102", f"Mutable default argument in function '{node.name}'", node.lineno)

        self.current_function = node.name  # set the current function name
        self.functions[node.name] = {'returns': [], 'lineno': node.lineno}  # initialize function return tracking
        self.scopes.append({})            # create a new scope for the function
        prev_scope = self.current_scope   # save the previous scope
        self.current_scope = self.scopes[-1]  # set current scope to function scope
        # add function parameters to the current scope
        for arg in node.args.args:
            self.current_scope[arg.arg] = 'param'
        if node.args.vararg:
            self.current_scope[node.args.vararg.arg] = 'param'
        if node.args.kwarg:
            self.current_scope[node.args.kwarg.arg] = 'param'
        for arg in node.args.kwonlyargs:
            self.current_scope[arg.arg] = 'param'
        self.generic_visit(node)          # visit the function body
        self.scopes.pop()                 # restore the previous scope
        self.current_scope = prev_scope
        self.check_return_consistency(node)  # check for inconsistent return statements
        self.current_function = None      # clear the current function

    def check_return_consistency(self, node):
        """check for inconsistent return statements within a function.
        ensures that the function consistently either returns a value or not.
        """
        returns = self.functions[node.name]['returns']  # retrieve the list of return statements
        if returns:
            if not all(returns) and any(returns):
                # report inconsistency if there's a mix of returns with and without values
                self._add_issue("W0631", f"Inconsistent return statements in function '{node.name}'", node.lineno)

    def visit_Return(self, node):
        """record return statements to analyze consistency within the function."""
        if self.current_function:
            has_value = node.value is not None  # determine if return statement has a value
            self.functions[self.current_function]['returns'].append(has_value)
        self.generic_visit(node)

    def visit_Assign(self, node):
        """handle variable assignments and track them for usage analysis. Check E731."""
        if isinstance(node.value, ast.Lambda):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                self._add_issue("E731", f"Do not assign a lambda expression, use a 'def' for '{node.targets[0].id}'", node.lineno)

        for target in node.targets:
            self.handle_assignment(target, is_module_level=isinstance(node.parent, ast.Module))
        self.generic_visit(node)

    def handle_assignment(self, target, is_module_level=False):
        """process different types of assignment targets (e.g., variables, tuples).
        this function tracks variable assignments and warns if a built-in name is being shadowed.
        Checks for variable naming conventions (snake_case) and constant naming (UPPER_CASE).
        """
        if isinstance(target, ast.Name):
            var_name = target.id
            if var_name in self.built_in_names:
                # warn if assigning to a built-in name
                self._add_issue("W0622", f"Redefining built-in '{var_name}'", target.lineno)
            
            # Naming conventions
            # Heuristic: if module level and all upper, it's a constant. Otherwise, snake_case.
            is_likely_constant = is_module_level and var_name.isupper() and not var_name.islower()

            if is_likely_constant:
                if not re.match(r'^[A-Z_][A-Z0-9_]*$', var_name):
                    self._add_issue("C0103", f"Constant '{var_name}' should be in UPPER_CASE_WITH_UNDERSCORES", target.lineno)
            elif not (var_name.startswith('__') and var_name.endswith('__')): # Allow dunder names
                 # Exclude class names which are handled in visit_ClassDef
                if var_name not in self.class_names and not re.match(r'^[a-z_][a-z0-9_]*$', var_name):
                    # Check if it's a CapWords name that might be a class instance, be less strict here
                    # or assume variables should always be snake_case unless it's a known class type.
                    # For simplicity, we'll flag if not snake_case and not a known class name.
                    if not re.match(r'^[A-Z][a-zA-Z0-9]*$', var_name): # Avoid flagging CapWords if it's not a class
                        self._add_issue("C0103", f"Variable '{var_name}' should be in snake_case", target.lineno)


            self.current_scope[var_name] = 'assigned'     # mark variable as assigned in current scope
            self.assignments[var_name] = target.lineno    # record the line number of assignment
            if is_module_level:
                self.module_level_assignments[var_name] = target.lineno
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self.handle_assignment(elt, is_module_level)  # recursively handle each element
        elif isinstance(target, ast.Attribute):
            pass  # skip assignments to attributes (e.g., self.value)

    def visit_Name(self, node):
        """check if variables are defined before use and track usages."""
        if isinstance(node.ctx, ast.Load):
            # variable is being read
            if not self.is_name_defined(node.id):
                if node.id not in self.built_in_names:
                    # report error if variable is used before assignment
                    self._add_issue("E0602", f"Undefined variable '{node.id}'", node.lineno)
            self.usages[node.id] = node.lineno  # record variable usage
            
            # Check if the used name corresponds to an import
            for imp_name, _ in self.imports:
                if node.id == imp_name:
                    self.used_imports.add(imp_name) # Mark the specific name as used
                    break
        elif isinstance(node.ctx, ast.Store):
            # variable is being assigned - handled by visit_Assign/handle_assignment
            # but ensure it's marked in scope if not already
            if node.id not in self.current_scope:
                 self.current_scope[node.id] = 'assigned'
        self.generic_visit(node)

    def is_name_defined(self, name):
        """determine if a variable or name is defined in accessible scopes.
        checks local scopes, global scope, class names, imports, and built-in names.
        """
        for scope in reversed(self.scopes):
            if name in scope:
                return True  # found in local or enclosing scope
        if name in self.global_scope:
            return True     # found in global scope
        if name in self.class_names:
            return True     # name matches a class
        for imp_name, _ in self.imports: # Check against stored import names
            if name == imp_name:
                return True
        if name in self.built_in_names:
            return True     # name matches a built-in
        return False        # name is undefined

    def visit_Global(self, node):
        """record variables declared as global."""
        for name in node.names:
            self.global_vars.add(name)            # add to global variables set
            self.global_scope[name] = 'global'    # mark in global scope

    def visit_Nonlocal(self, node):
        """record variables declared as nonlocal."""
        for name in node.names:
            self.nonlocal_vars.add(name)          # add to nonlocal variables set

    def visit_For(self, node):
        """check for deeply nested loops and create a new scope for loop variables."""
        self.loop_depth += 1
        if self.loop_depth > 2: # This is a custom rule, not strictly PEP 8
            # report if loop nesting is too deep
            self._add_issue("C0200", f"Nested loop too deep", node.lineno) # Example custom code
        self.scopes.append({})                    # create a new scope for the loop
        prev_scope = self.current_scope
        self.current_scope = self.scopes[-1]
        self.handle_assignment(node.target, is_module_level=isinstance(node.parent, ast.Module)) # handle the loop variable assignment
        self.generic_visit(node)
        self.scopes.pop()                         # restore the previous scope
        self.current_scope = prev_scope
        self.loop_depth -= 1

    def visit_While(self, node):
        """check for infinite loops and deeply nested loops; create a new scope."""
        self.loop_depth += 1
        if self.loop_depth > 2: # Custom rule
            self._add_issue("C0200", f"Nested loop too deep", node.lineno)
        if isinstance(node.test, ast.Constant) and node.test.value is True:
            # detect possible infinite loops without a break statement
            has_break = any(isinstance(child, ast.Break) for child in ast.walk(node))
            if not has_break:
                self._add_issue("W0104", f"Possible infinite loop (while True without break)", node.lineno)
        self.scopes.append({})                    # create a new scope for the loop
        prev_scope = self.current_scope
        self.current_scope = self.scopes[-1]
        self.generic_visit(node)
        self.scopes.pop()                         # restore the previous scope
        self.current_scope = prev_scope
        self.loop_depth -= 1

    def visit_Compare(self, node):
        """Check for PEP 8 comparison issues: E711, E712, E721."""
        # E711: comparison to None should be 'is None' or 'is not None'
        for i, op in enumerate(node.ops):
            comparator = node.comparators[i]
            if isinstance(op, (ast.Eq, ast.NotEq)):
                left_is_none = isinstance(node.left if i == 0 else node.comparators[i-1], ast.Constant) and \
                               (node.left if i == 0 else node.comparators[i-1]).value is None
                right_is_none = isinstance(comparator, ast.Constant) and comparator.value is None
                if left_is_none or right_is_none:
                    self._add_issue("E711", "Comparison to None should be 'is None' or 'is not None'", node.lineno)

                # E712: comparison to True/False should be 'is True/False' or 'if cond:'
                left_is_bool = isinstance(node.left if i == 0 else node.comparators[i-1], ast.Constant) and \
                               isinstance((node.left if i == 0 else node.comparators[i-1]).value, bool)
                right_is_bool = isinstance(comparator, ast.Constant) and isinstance(comparator.value, bool)
                if left_is_bool or right_is_bool:
                     self._add_issue("E712", "Comparison to True/False should be 'is True/False' or direct use of boolean", node.lineno)
            
            # E721: do not compare types, use isinstance()
            if isinstance(op, ast.Is) or isinstance(op, ast.IsNot): # Also check 'is' for type comparison
                left_is_type_call = isinstance(node.left if i == 0 else node.comparators[i-1], ast.Call) and \
                                    isinstance((node.left if i == 0 else node.comparators[i-1]).func, ast.Name) and \
                                    (node.left if i == 0 else node.comparators[i-1]).func.id == 'type'
                right_is_type_call = isinstance(comparator, ast.Call) and \
                                     isinstance(comparator.func, ast.Name) and \
                                     comparator.func.id == 'type'
                if left_is_type_call and right_is_type_call:
                     self._add_issue("E721", "Do not compare types directly, use isinstance()", node.lineno)
        self.generic_visit(node)


    def visit_BinOp(self, node):
        """check for division by zero errors in binary operations."""
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            if isinstance(node.right, ast.Constant) and node.right.value == 0:
                # report division by zero error
                self._add_issue("E0001", f"Division by zero", node.lineno) # Using a generic error code
        self.generic_visit(node)

    def visit_Try(self, node):
        """check try-except blocks for empty except blocks and broad exceptions."""
        for handler in node.handlers:
            if not handler.body:
                # report empty except block
                self._add_issue("W0702", f"Empty except block", handler.lineno)
            if handler.type is None:
                # report bare except clause (E722)
                self._add_issue("E722", f"Do not use bare 'except:'", handler.lineno)
            elif isinstance(handler.type, ast.Name) and handler.type.id == 'Exception':
                # report catching of broad exception 'exception'
                self._add_issue("W0703", f"Catching too general exception 'Exception'", handler.lineno)
        self.generic_visit(node)

    def visit_Call(self, node):
        """check for resource leaks when using 'open' without a 'with' statement and mark used imports."""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name == 'open':
                # Check if 'open' is part of a 'with' statement
                current_node = node
                in_with_statement = False
                while hasattr(current_node, 'parent'):
                    if isinstance(current_node.parent, ast.With):
                        # Check if this 'open' call is one of the items in the 'with'
                        for item in current_node.parent.items:
                            if item.context_expr == current_node:
                                in_with_statement = True
                                break
                        if in_with_statement:
                            break 
                    current_node = current_node.parent
                if not in_with_statement:
                    self._add_issue("W6001", f"File opened without 'with' statement", node.lineno) # Custom warning code

            # Mark import as used
            for imp_name, _ in self.imports:
                if func_name == imp_name:
                    self.used_imports.add(imp_name)
                    break
        elif isinstance(node.func, ast.Attribute): # For method calls like 'module.function()'
            # Try to resolve the base module/object name
            obj = node.func.value
            if isinstance(obj, ast.Name):
                for imp_name, _ in self.imports:
                    if obj.id == imp_name:
                        self.used_imports.add(imp_name)
                        break
        self.generic_visit(node)

    def report_unused(self):
        """report variables that are assigned but never used in the code."""
        for var, lineno in self.assignments.items():
            # Check if var is in any import name (first element of tuple)
            is_an_import = any(var == imp_name for imp_name, _ in self.imports)
            if var not in self.usages and not is_an_import:
                if var not in self.built_in_names:
                    # report unused variable
                    self._add_issue("W0612", f"Unused variable '{var}'", lineno)

# Removed the duplicate generic_visit method that was here.

def analyze_code(source_code):
    """analyze the provided source code for issues using the codeanalyzer.
    args:
        source_code (str): the python source code to be analyzed.
    returns:
        list: a list of detected issues in the code.
    """
    try:
        tree = ast.parse(source_code)         # parse the source code into an ast
        analyzer = CodeAnalyzer()             # create an instance of the analyzer
        analyzer.visit(tree)                  # visit each node in the ast
        analyzer.report_unused()              # report any unused variables
        return analyzer.issues                # return the list of issues found
    except SyntaxError as e:
        # return syntax error details if parsing fails
        return [f"E999: SyntaxError: {e.msg} at line {e.lineno}, column {e.offset}"]