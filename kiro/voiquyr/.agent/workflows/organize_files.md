---
description: Organize test files into a dedicated tests directory
---

# Steps to reorganize the project

1. Create a `tests` directory at the project root.
   // turbo
   ```
   mkdir tests
   ```
2. Move all test files (`test_*.py`) from the project root into the `tests` directory.
   // turbo-all
   ```
   move test_*.py tests\
   ```
3. (Optional) Add an empty `__init__.py` inside `tests` to make it a package.
   // turbo
   ```
   type nul > tests\__init__.py
   ```
4. Verify that imports in test files still reference the `src` package (they already do), so no code changes are required.
5. Run the test suite to ensure nothing is broken.
   // turbo
   ```
   pytest
   ```
