from glom import glom
from collections import deque


o = glom([1,2,3], lambda x: deque(x, 10))
print(o)