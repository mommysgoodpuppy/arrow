class Router:
    def __init__(self):
        self.routes = {}
        self.values = {}
        self.scopes = {}

    def debug(self, msg):
        print(f"DEBUG: {msg}")

    def execute(self, code):
        blocks = self._parse_blocks(code)
        self.debug(f"Parsed blocks: {blocks}")
        for block in blocks:
            self._process(block)

    def _parse_blocks(self, code):
        lines = [
            line.strip()
            for line in code.split("\n")
            if line.strip() and not line.strip().startswith("#")
        ]
        blocks, stack, current = [], [], []
        for line in lines:
            if line.endswith("{"):
                stack.append(line)
                current.append(line)
            elif line.startswith("}"):
                stack.pop()
                current.append(line)
                if not stack:
                    blocks.append(current.copy())
                    current.clear()
            else:
                current.append(line)
        blocks += current if current else []
        return blocks

    def _process(self, block):
        if isinstance(block, list):
            target = block[0].split(">")[0].strip()
            self.debug(f"Processing block for {target}")
            scope = {}
            self.scopes[target] = scope
            for line in block[1:-1] if block[0].endswith("{") else block:
                parts = [p.strip() for p in line.split(">")]
                if len(parts) == 2:
                    if parts[1].isdigit():
                        scope[parts[0]] = int(parts[1])
                    elif parts[1].startswith('"') and parts[1].endswith('"'):
                        scope[parts[0]] = parts[1][1:-1]  # Remove quotes for string
                    else:
                        self.routes[f"{target}.{parts[0]}"] = " > ".join(parts[1:])
                else:
                    self.routes[f"{target}.{parts[0]}"] = " > ".join(parts[1:])
            self.debug(f"Block scope: {scope}")
            self.debug(f"Updated routes: {self.routes}")
        else:
            self._route(block)

    def _route(self, line):
        self.debug(f"Routing: {line}")
        parts = [p.strip() for p in line.split(">")]

        if parts[0] == "systemPrint":
            value = parts[1] if len(parts) > 1 else None
            value = self._resolve_value(value)
            print(value)
            return

        if len(parts) == 2:
            if parts[1].isdigit():
                self.values[parts[0]] = int(parts[1])
                return
            elif parts[1].startswith('"') and parts[1].endswith('"'):  # Handle string
                self.values[parts[0]] = parts[1][1:-1]
                return

        route_key = f"{parts[0]}.{parts[1]}" if len(parts) > 1 else parts[0]
        self.debug(f"Route key: {route_key}")

        if route_key in self.routes:
            action = self._substitute(self.routes[route_key], parts)
            self.debug(f"Following route {route_key} -> {action}")
            self._route(action)

    def _resolve_value(self, value):
        if value and value.startswith("@"):
            return str(self.values.get(value[1:], value))
        return value

    def _substitute(self, action, parts):
        target = parts[0]
        args = parts[2:]
        scope = self.scopes.get(target, {})
        for var, val in scope.items():
            action = action.replace(f"@{var}", str(val))
        for i, arg in enumerate(args):
            action = action.replace(f"arg{i}", arg)
        return action


# Test
test_code = """
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

print("Running test program:")
print("--------------------")
Router().execute(test_code)
