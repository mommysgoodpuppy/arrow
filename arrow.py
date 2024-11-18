import re


class Router:
    def __init__(self):
        self.routes = {}
        self.deferred_routes = {}
        self.scopes = [{}]

    def debug(self, msg):
        print(f"DEBUG: {msg}")

    def execute(self, code):
        blocks, lines = self._parse_blocks(code)
        self.debug(f"Parsed blocks: {blocks}")
        for block in blocks:
            self._process_block(block)
        for line in lines:
            self._execute_line(line)

    def _parse_blocks(self, code):
        lines = [
            line.strip()
            for line in code.strip().split("\n")
            if line.strip() and not line.strip().startswith("#")
        ]
        blocks, current_block, stack = [], [], []
        remaining_lines = []
        for line in lines:
            if line.endswith("{"):
                stack.append("{")
                current_block.append(line)
            elif line == "}":
                stack.pop()
                current_block.append(line)
                if not stack:
                    blocks.append(current_block)
                    current_block = []
            elif stack:
                current_block.append(line)
            else:
                remaining_lines.append(line)
        return blocks, remaining_lines

    def _process_block(self, block):
        header = block[0]
        target = header.split(">")[0].strip()
        self.scopes.append({})
        self.debug(f"Processing block for '{target}'")

        def process_instant_execution(line):
            # Remove the leading > and create execution line
            exec_line = line[1:].strip()
            # Resolve any @variables in the line
            resolved_line = self._substitute_args(exec_line, [])
            self.debug(f"Found instant execution line: '{exec_line}' resolved to '{resolved_line}'")

            # First, create the route from the line (without the leading >)
            parts = [p.strip() for p in exec_line.split(">")]
            if len(parts) >= 2:
                route_key = f"{target}.{parts[0]}"
                route_value = ">".join(parts[1:])
                self.routes[route_key] = route_value
                self.debug(f"Created route from instant execution: {route_key} = {route_value}")

            # Then handle execution by forcing systemPrint as the target
            if resolved_line.startswith(">"):
                process_instant_execution(resolved_line)
            else:
                # Split into parts but keep systemPrint as the target
                parts = [p.strip() for p in resolved_line.split(">")]
                if len(parts) >= 3 and parts[1] == "systemPrint":
                    exec_line = f"systemPrint > {parts[2]}"
                    self.debug(f"Executing modified line: {exec_line}")
                    self._execute_line(exec_line)
        
        for line in block[1:-1]:
            if line.startswith(">"): # Handle instant execution
                process_instant_execution(line)
            elif ">=" in line:
                var, func_call = map(str.strip, line.split(">="))
                new_line = f"{func_call} > {target} > {var}"
                self.debug(f"Executing callback assignment: '{new_line}'")
                self._execute_line(new_line)
            else:
                parts = [p.strip() for p in line.split(">")]
                if len(parts) >= 2:
                    key, value = parts[0], ">".join(parts[1:])
                    if value.startswith('"') and value.endswith('"'):
                        self.scopes[-1][key] = value[1:-1]
                        self.debug(
                            f"Assigned '{key}' = '{value[1:-1]}' in current scope"
                        )
                    else:
                        route_key = f"{target}.{key}"
                        if key.startswith("arg"):
                            self.deferred_routes[route_key] = value
                            self.debug(f"Deferred route: '{route_key}' = '{value}'")
                        else:
                            self.routes[route_key] = value
                            self.debug(f"Assigned route: '{route_key}' = '{value}'")
        
        self.debug(f"Block scope: {self.scopes[-1]}")
        self.debug(f"Current Routes: {self.routes}")
        self.debug(f"Deferred Routes: {self.deferred_routes}")

    def _execute_line(self, line):
        self.debug(f"Executing line: '{line}'")
        parts = [p.strip() for p in line.split(">")]
        if not parts:
            self.debug(f"No action for line: '{line}'")
            return

        target = parts[0]
        action = parts[1] if len(parts) > 1 else None
        args = parts[2:] if len(parts) > 2 else []

        if action:
            route_key = f"{target}.{action}"
            route_action = self.routes.get(route_key)
            if route_action:
                substituted_action = self._substitute_args(route_action, args)
                self.debug(
                    f"Executing route: '{route_key}' with substituted action: '{substituted_action}'"
                )
                return self._execute_line(substituted_action)
            elif len(parts) == 3 and not action.startswith('"'):
                var = action
                value = self._substitute_args(args[0], [])
                resolved_value = self._resolve_value(value)
                self.scopes[-1][var] = resolved_value
                self.debug(f"Assigned '{var}' = '{resolved_value}' in current scope")
                return resolved_value
            elif target == "systemPrint":
                value = self._substitute_args(action, args)
                self.debug(f"Executing 'systemPrint' with value: '{value}'")
                self.systemPrint(value)
            else:
                # Execute regular route first
                result = self._execute_deferred_routes(target, action, args)

                # Now check for arg0 match specifically
                route_key = f"{target}.arg0"
                if route_key in self.deferred_routes:
                    route_action = self.deferred_routes[route_key]
                    transformed_action = route_action.replace("arg0", action)
                    self.debug(
                        f"Executing arg0 deferred route: '{route_key}' with action: '{transformed_action}'"
                    )
                    self._execute_line(transformed_action)
                return result

        else:
            return self._resolve_value(target)

    def _execute_deferred_routes(self, target, action, args):
        for i in range(1, len(args) + 1):  # Start from 1 to skip arg0
            route_key = f"{target}.arg{i}"
            if route_key in self.deferred_routes:
                route_action = self.deferred_routes[route_key]
                arg_value = args[i - 1]
                if arg_value == action:  # Check if argN matches arg0 (action)
                    transformed_action = route_action.replace(f"arg{i}", arg_value)
                    self.debug(
                        f"Transformed deferred route: '{route_key}' to '{transformed_action}'"
                    )
                    substituted_action = self._substitute_args(transformed_action, args)
                    self.debug(
                        f"Executing transformed deferred route: '{substituted_action}'"
                    )
                    return self._execute_line(substituted_action)
        self.debug(
            f"No matching route or deferred route found for: {target} > {action} > {' > '.join(args)}"
        )
        return None

    def _substitute_args(self, action, args):
        def arg_replacer(match):
            index = int(match.group(1))
            if index < len(args):
                return args[index]
            else:
                return ""

        def at_replacer(match):
            var_name = match.group(1)
            return self._resolve_value(f"@{var_name}")

        pattern = re.compile(r"arg(\d+)")
        substituted_action = pattern.sub(arg_replacer, action)

        at_pattern = re.compile(r"@(\w+)")
        substituted_action = at_pattern.sub(at_replacer, substituted_action)

        return substituted_action

    def _resolve_value(self, value):
        if value.startswith("@"):
            var_name = value[1:]
            for scope in reversed(self.scopes):
                if var_name in scope:
                    return scope[var_name]
            return "none"
        return value

    def systemPrint(self, value):
        print(value)


# Test cases
test_code1 = """
funcwithsecret > {
    secret > "hello world"
    true > arg0 > arg1 > @secret
}

getsecret > {
    value >= funcwithsecret > true
    true > systemPrint > @value
}

getsecret > true
"""

test_code2 = """
funcwithsecret > {
    secret > "hello world"
    true > arg0 > arg1 > @secret
}

getsecret > {
    true > funcwithsecret > true > getsecret > setpublicsecret
    setpublicsecret > systemPrint > arg0
}
getsecret > true
"""

test_code3 = """
getsecret > {
    value >= funcwithsecret > true
    true > systemPrint > @value
    arg1 > systemPrint > "else"
}

getsecret > "st" > "st"
"""

test_code4 = """
getsecret > {
    value >= funcwithsecret > true
    true > systemPrint > @value
    arg0 > systemPrint > "else"
}

getsecret > "st"
"""

test_code_match_countdownX = """
countdown > {
    zero > systemPrint > "Countdown finished!"
    arg0 > substract > arg0 > countdown
}

substract > {
    five > arg0 > four
    four > arg0 > three
    three > arg0 > two
    two > arg0 > one
    one > arg0 > zero
}

# Start the countdown from 5
countdown > five
"""


test_codesucc = """
# Define zero and successor function
zero > {
    true > arg0 > arg1
}

succ > {
    true > arg0 > arg1 > arg2
    true > @arg0 > succ > @arg1 > @arg2
}

# Define increment operation
increment > {
    true > succ > arg0 > arg1
}

# Define a function to convert our number representation to a string
to_string > {
    zero > arg0 > arg1 > "zero"
    true > arg0 > to_string_helper > 1 > arg1
}

to_string_helper > {
    zero > arg0 > arg1 > arg2
    true > arg2 > @arg1
    true > arg0 > to_string_helper > @arg1 > plusOne > arg2
}

plusOne > {
    true > arg0 > add > 1
}

add > {
    0 > arg0 > arg1 > @arg1
    true > arg0 > arg1 > add > subtract > @arg0 > 1 > succ > @arg1
}

subtract > {
    0 > arg0 > arg1 > @arg0
    true > arg0 > arg1 > subtract > @arg0 > 1 > @arg1
}

# Test increment
test_increment > {
    one >= succ > zero
    two >= succ > one
    result >= increment > two
    string_result >= to_string > @result
    true > systemPrint > "Increment of two is: @string_result"
}

# Run the test
test_increment > true
"""

testcodeP = """
parallel > {
    > print1 > systemPrint > "Branch One Started"
    > print2 > systemPrint > "Branch Two Started"
    
    # Normal routes can still exist
    arg0 > systemPrint > "Normal execution"
}

meta3 > {
    pattern > "> print > systemPrint > \"meta3\""
    > @pattern
}
metaoriginal > {
    > print > systemPrint > "metaorig"
}

metameta > {
    gen > "> > print > systemPrint > \"Double meta!\""
    > @gen     
}


parallel > true

"""

print("Running recursive countdown test:")
print("--------------------")
Router().execute(testcodeP)


print("Running test programs:")
print("--------------------")
Router().execute(test_code1)
print("--------------------")
Router().execute(test_code2)
print("--------------------")
Router().execute(test_code3)
print("--------------------")
Router().execute(test_code4)
