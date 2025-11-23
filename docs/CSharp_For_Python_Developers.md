# C# for Python Developers - Quick Reference

## Data Types

| Python | C# | Example |
|--------|-----|---------|
| `int` | `int` | `int count = 5` |
| `float` | `double` | `double price = 9.99` |
| `str` | `string` | `string name = "Pump"` |
| `bool` | `bool` | `bool isActive = true` |
| `None` | `null` | `string? unit = null` |
| `List[int]` | `List<int>` | `List<int> ids = new()` |
| `Dict[str, int]` | `Dictionary<string, int>` | `Dictionary<string, int> map = new()` |

## Key Syntax Differences
```python
# PYTHON
def get_equipment(id):
    equipment = database.find(id)
    return equipment
```
```csharp
// C#
public Equipment GetEquipment(int id)
{
    var equipment = _database.Find(id);
    return equipment;
}
```

## Common Patterns

### Variables
```python
# Python - dynamic typing
name = "Pump"
count = 5
```
```csharp
// C# - static typing
string name = "Pump";
int count = 5;

// Or with type inference
var name = "Pump";  // C# figures out it's a string
```

### Collections
```python
# Python
items = [1, 2, 3]
items.append(4)
filtered = [x for x in items if x > 2]
```
```csharp
// C#
var items = new List<int> { 1, 2, 3 };
items.Add(4);
var filtered = items.Where(x => x > 2).ToList();
```

### String Formatting
```python
# Python
message = f"Equipment {name} has {count} items"
```
```csharp
// C#
string message = $"Equipment {name} has {count} items";
```

## Entity Framework (C#) vs SQLAlchemy (Python)
```python
# Python + SQLAlchemy
session = Session()
equipment = session.query(Equipment).filter(Equipment.id == 1).first()
session.add(new_equipment)
session.commit()
```
```csharp
// C# + Entity Framework
var equipment = await _context.Equipment.FindAsync(1);
_context.Equipment.Add(newEquipment);
await _context.SaveChangesAsync();
```

## Quick Translation Table

| Task | Python | C# |
|------|--------|-----|
| Print | `print("hello")` | `Console.WriteLine("hello")` |
| Create list | `items = []` | `var items = new List<Item>()` |
| Add to list | `items.append(x)` | `items.Add(x)` |
| Filter | `[x for x in items if x > 5]` | `items.Where(x => x > 5).ToList()` |
| Check null | `if x is None:` | `if (x == null)` |
| String contains | `if "pump" in text:` | `if (text.Contains("pump"))` |
| List length | `len(items)` | `items.Count` |

## Important Notes

1. **Semicolons**: Every statement ends with `;`
2. **Curly braces**: Use `{}` for code blocks (not indentation)
3. **Type declaration**: Must specify types or use `var`
4. **Async**: Returns `Task<T>` instead of just using `async def`
5. **Properties**: `{ get; set; }` is like Python's `@property`

## When You See This in C#...

- `public` = accessible from anywhere (like Python without `_`)
- `private` = only accessible within class (like Python's `_variable`)
- `async Task<T>` = Python's `async def` that returns `T`
- `await` = same as Python's `await`
- `var` = let C# figure out the type
- `?` after type = can be `null` (like Python's `Optional`)
- `=>` = lambda (like Python's `lambda`)

