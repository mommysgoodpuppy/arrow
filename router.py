class Router:
    def __init__(self):
        self.routes = {}
        self.debug = True

    def log(self, msg):
        if self.debug:
            print(f"DEBUG: {msg}")

    def send(self, line):
        self.log(f"Processing: {line}")
        if not ">" in line:
            return

        parts = line.split(">")
        parts = [p.strip() for p in parts]

        # Route the message through the chain
        for i in range(len(parts) - 1):
            source = parts[i]
            target = parts[i + 1]
            self.log(f"Routing {source} to {target}")

            if source in self.routes:
                target = f"{self.routes[source]} {target}"

            self.routes[source] = target
            self.log(f"Route table: {self.routes}")


# Test simple routing
test1 = """
A > B > C 
B > D
A > hello
"""

print("Test 1: Simple routing")
print("---------------------")
r = Router()
for line in test1.splitlines():
    if line.strip():
        r.send(line)

# Test with function-like behavior
test2 = """
greeter > print > hello
greeter > print > world
"""

print("\nTest 2: Function-like behavior")
print("---------------------")
r = Router()
for line in test2.splitlines():
    if line.strip():
        r.send(line)
