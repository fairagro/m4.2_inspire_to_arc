from arctrl import OntologyAnnotation
import inspect

print("OntologyAnnotation init signature:", inspect.signature(OntologyAnnotation.__init__))
print("OntologyAnnotation doc:", OntologyAnnotation.__doc__)

# Try instantiation
try:
    oa = OntologyAnnotation(TermName="Test")
    print("Keyword init worked")
except Exception as e:
    print(f"Keyword init failed: {e}")

try:
    oa = OntologyAnnotation("Test")
    print("Positional init worked")
except Exception as e:
    print(f"Positional init failed: {e}")
